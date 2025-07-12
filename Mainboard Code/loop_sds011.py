import socket
import machine
import time
import sys
import json
import struct
import re
from machine import UART, Pin, SoftI2C, SoftSPI, deepsleep, ADC
from machine import RTC, WDT
import sdcard
import esp32
import os
import ubinascii
from lcd_api import LcdApi
from i2c_lcd import I2cLcd
import onewire, ds18x20
import sim7600
import gc
import ledpm25
gc.collect()
rtc = RTC()
machine.freq(80000000)
global strlcd
storage = esp32.NVS("storage")
RAIN=False
TH=False
Ultrasonic = False
import sds011
uart = UART(2, baudrate=9600, tx=14, rx=13)
dust_sensor = sds011.SDS011(uart)
dust_sensor.sleep()
SDS011=True
#phien ban dung cho T-A7670G
ver="FAS-2.0DA40225"
if sim7600.sim7600_a7670:
    version=ver+"S76"
    LED = machine.Pin(12, machine.Pin.OUT)
    BUZZER = machine.Pin(25, machine.Pin.OUT)

else:
    version=ver+"A76"
if RAIN:
    version=version+"RA"
elif Ultrasonic:
    version=version+"UL"
elif SDS011:
    version=version+"SDS"
    sht30connect=True
    from sht30 import SHT30
    try:
        sensor_sht30 = SHT30()
        temperature, humidity = sensor_sht30.measure()
        print('Temperature:', temperature, 'ºC, RH:', humidity, '%')
        sht30connect = True
    except Exception as e:
        print('Error FAS-SHT30:',str(e))
else:
    if TH:
        version=version+"TH"
    else:
        version=version+"TT"

def measure_distance(TRIG_PIN,ECHO_PIN):
    # Khởi tạo chân GPIO
    trig = machine.Pin(TRIG_PIN, machine.Pin.OUT)
    echo = machine.Pin(ECHO_PIN, machine.Pin.IN)
    # Gửi xung 10us để kích hoạt cảm biến
    trig.on()  # Bật chân Trig
    time.sleep_us(10)
    trig.off()  # Tắt chân Trig
    
 # Đợi tín hiệu phản hồi
    pulse_start = time.ticks_us()
    timeout = pulse_start + 50000  # 50ms timeout

    # Kiểm tra tín hiệu bắt đầu
    while echo.value() == 0:
        pulse_start = time.ticks_us()
        if pulse_start > timeout:  # Kiểm tra timeout
            print("Lỗi: Không nhận được tín hiệu từ cảm biến.")
            return 0
    
    pulse_end = time.ticks_us()  # Lưu thời gian bắt đầu nhận tín hiệu

    # Kiểm tra tín hiệu kết thúc
    timeout = pulse_end + 50000  # 50ms timeout
    while echo.value() == 1:
        pulse_end = time.ticks_us()
        if pulse_end > timeout:  # Kiểm tra timeout
            print("Lỗi: Không nhận được tín hiệu từ cảm biến.")
            return 0

    # Tính toán khoảng cách
    pulse_duration = time.ticks_diff(pulse_end, pulse_start)
    distance = (pulse_duration * 0.0343) / 2  # Đổi xung thành khoảng cách (cm)
    return distance

def beep(duration=0.1):
    BUZZER.on()  # Bật buzzer
    time.sleep(duration)  # Đợi một khoảng thời gian
    BUZZER.off()  # Tắt buzzer
    time.sleep(duration)  # Đợi một khoảng thời gian trước khi beep lại
    
# Khởi tạo ADC trên chân GPIO 36
adcpow = ADC(Pin(36))
adcpow.atten(ADC.ATTN_11DB)    # Giới hạn điện áp từ 0-2.2V
# Khởi tạo ADC trên chân GPIO 35
adcbat = ADC(Pin(35))
adcbat.atten(ADC.ATTN_11DB)    # Giới hạn điện áp từ 0-2.2V
# Khởi tạo Watchdog Timer với thời gian chờ (timeout) là 200 giây
wdt = WDT(timeout=200000)
# Kiểm tra nguyên nhân reset
def check_reset_reason():
    reset_reason = machine.reset_cause()
    if reset_reason == machine.PWRON_RESET:
        return "PWRON_RESET"
    elif reset_reason == machine.WDT_RESET:
        return "WDT_RESET"
    elif reset_reason == machine.SOFT_RESET:
        return "SOFT_RESET"
    elif reset_reason == machine.HARD_RESET:
        return "HARD_RESET"
    elif reset_reason == machine.PIN_WAKE:
        return "GPIO_RESET"
    elif reset_reason == machine.DEEPSLEEP_RESET:
        return "DEEPSLEEP_RESET"
    else:
        return "RESET"
check_reset = check_reset_reason()
print(check_reset )        
if RAIN:
    # Biến toàn cục để đếm xung
    first_run = True
    pulse_count = 0
    hourly_count = 0
    daily_count = 0
    last_pulse_time = time.ticks_ms()
    sleep_duration = 10 * 60 * 1000  # 10 phut (thời gian ngủ tính bằng ms)
    timeout_duration = 5 * 60 * 1000  # 5 phút (thời gian không có xung)
    # Hàm để đọc số lượng xung từ RTC
    def load_rain_data():
        try:
            pulse_count = storage.get_i32('pulse_count')
            hourly_count = storage.get_i32('hourly_count')
            daily_count = storage.get_i32('daily_count')
        except Exception as e:
            storage.set_i32('pulse_count', 0)
            storage.set_i32('hourly_count', 0)
            storage.set_i32('daily_count', 0)
            print('fail storage')
            return 0, 0, 0
        return pulse_count, hourly_count, daily_count
    # Đọc số lượng xung khi khởi động
    pulse_count, hourly_count, daily_count = load_rain_data()
    '''if "PWRON_RESET" in check_reset:
        pulse_count += 1
        hourly_count +=1
        daily_count +=1
        last_pulse_time = time.ticks_ms()'''
    # Hàm để lưu trữ số lượng xung vào RTC
    def save_rain_data(pulse_count, hourly_count, daily_count):
        storage.set_i32('pulse_count', pulse_count)
        storage.set_i32('hourly_count', hourly_count)
        storage.set_i32('daily_count', daily_count)
    # Hàm xử lý interrupt
    def count_pulse(pin):
        global pulse_count, last_pulse_time, hourly_count, daily_count, first_run
        '''if first_run==True:
            time.sleep(1)
            first_run=False
            last_pulse_time = time.ticks_ms()
            print("First Run...")'''
            
        # Kiểm tra xem khoảng thời gian giữa các xung có đủ lớn không
        if time.ticks_ms() - last_pulse_time > 200:  # 200 ms là độ trễ tối thiểu
            pulse_count += 1
            hourly_count +=1
            daily_count +=1
            last_pulse_time = time.ticks_ms()
            save_rain_data(pulse_count, hourly_count, daily_count)
            print("Count pulse: ",str(pulse_count),str(hourly_count), str(daily_count))
    # Gán hàm xử lý interrupt cho chân GPIO 33
    pulse_in = machine.Pin(32, machine.Pin.IN, Pin.PULL_UP)
    pulse_in.irq(trigger=Pin.IRQ_FALLING, handler=count_pulse)
    esp32.wake_on_ext0(pin = pulse_in, level = esp32.WAKEUP_ALL_LOW)
    sht30connect=False
else:
    if TH:
        sht30connect=True
        from sht30 import SHT30
        try:
            sensor_sht30 = SHT30()
            temperature, humidity = sensor_sht30.measure()
            print('Temperature:', temperature, 'ºC, RH:', humidity, '%')
            sht30connect = True
        except Exception as e:
            print('Error FAS-SHT30:',str(e))
    else:
        ow = onewire.OneWire(Pin(33))
        ds = ds18x20.DS18X20(ow)
        roms = ds.scan()
        if len(roms)>0:
            sht30connect=False
            ds.convert_temp()
            time.sleep(1)
            for i, rom in enumerate(roms):
                print("Temp{}: {} oC".format(i, ds.read_temp(rom)))
        else:
           print('Not DS18B20:')
       
I2C_ADDR = 0x27
totalRows = 4
totalColumns = 20
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=10000)     #initializing the I2C method for ESP32
lcdconnect = False
try:
    lcd = I2cLcd(i2c, I2C_ADDR, totalRows, totalColumns)
    lcd.backlight_on()
    lcdconnect = True
except Exception as e:
    print('Error LCD:',str(e))
    lcdconnect = False

'''
from umodbus.serial import Serial as ModbusRTUMaster
host = ModbusRTUMaster(
    pins=(18, 19),      # given as tuple (TX, RX), check MicroPython port specific syntax
    # baudrate=9600,    # optional, default 9600
    # data_bits=8,      # optional, default 8
    # stop_bits=1,      # optional, default 1
    # parity=None,      # optional, default None
    # ctrl_pin=12,      # optional, control DE/RE
    # uart_id=1         # optional, see port specific documentation
)
slave_addr = 1
hreg_address = 257
register_qty = 1
register_value = host.read_holding_registers(
    slave_addr=slave_addr,
    starting_addr=hreg_address,
    register_qty=register_qty,
    signed=False)
print('Status of HREG {}: {}'.format(hreg_address, register_value))
hreg_address = 259
register_qty = 1
register_value = host.read_holding_registers(
    slave_addr=slave_addr,
    starting_addr=hreg_address,
    register_qty=register_qty,
    signed=False)
print('Status of HREG {}: {}'.format(hreg_address, register_value))
'''
def led_blink():
    if LED.value()==1:
        LED.value(0)
    else:
        LED.value(1)
        
def check_at():
    response = sim7600.send_at_command('AT')
    if response is None or 'ERROR' in response:
        #led_blink()
        return False
    elif 'OK' in response:
        #LED.value(1)
        return True              

import config
Config=config.Setting()
Config.Load_setting()
'''Config.thingid='899890'
Config.thingkey='ZPN0YAK2W2ZKTFFD'
Config.Save_setting()'''
if lcdconnect:
    lcd.clear()
    strlcd=Config.devicename+'\nMID: '+Config.id+'\nCID: '+Config.thingid+'\n'+version
    lcd.putstr(strlcd)
#--------------------
global thing_entry_id
thing_entry_id=0

def get_status_thing(thingid):
    change=False
    thingresponse=""
    url = f"http://api.thingspeak.com/channels/{thingid}/status.json?results=3"
    response=sim7600.send_http_get(url)
    datajson=json.loads(response)
    feeds=datajson["feeds"]
    for feed in feeds:
        command=feed["status"]
        if(command is not None):
          print("Thing get status:",command)
          if((command.find("+Alarm on")!=-1 or command.find("+Bat alarm")!=-1)):
              Config.alarm=1
              thingresponse+="Inputs:"+str((Config.sms<<1) + Config.alarm)
              change=True
          elif((command.find("+Alarm off")!=-1 or command.find("+Tat alarm")!=-1)):
              Config.alarm=0
              thingresponse+="Inputs:"+str((Config.sms<<1) + Config.alarm)
              change=True
          elif 'Set' in command or 'Calib' in command or 'Key' in command:
              #print("Thing get status1:",command)
              pos=command.find('Settimeupload=') #Thingupload:10
              if(pos!=-1):
                  data=command.split('=')
                  if(len(data)==2):
                      try:
                          timeupload=int(float(data[1]))
                          if(timeupload>0):
                              Config.tupload=timeupload
                              thingresponse+=" Gettimeupload="+str(Config.tupload)+","
                              change=True
                      except Exception as e:
                          thingresponse='Error Settimeupload:'+str(e)
                      print("Thingresponse:",thingresponse)
              else:
                  pos=command.find('Setphone=') #Setphone=phone1,phone2…
                  if(pos!=-1):
                      data=command.split('=')
                      if(len(data)==2):
                          try:
                              getphone=""
                              phones=data[1].split(",")
                              for i in range(len(Config.tel)):
                                  if(Config.tel[i]!=phones[i]):
                                      Config.tel[i]=phones[i]
                                      change=True
                                  getphone += Config.tel[i] + ","
                              if(change):
                                  thingresponse+=" Getphone="
                                  thingresponse += getphone
                          except Exception as e:
                              thingresponse='Error Setphone:'+str(e)
                          print("Thingresponse:",thingresponse)
                  else:
                      pos=command.find('Setlow=') #Setlow= giá trị 1, giá trị 2…
                      if(pos!=-1):
                          data=command.split('=')
                          if(len(data)==2):
                              try:
                                  getlow=""
                                  lows=data[1].split(",")
                                  for i in range(len(lows)):
                                    if sim7600.is_float(lows[i]):
                                      Config.lowset[i]=float(lows[i])
                                      change=True
                                      getlow += str(Config.lowset[i])+ ","
                                  thingresponse+=" Getlow="
                                  thingresponse += getlow
                              except Exception as e:
                                  thingresponse='Error Setlow:'+str(e)
                              print("Thingresponse:",thingresponse)
                      else:
                          pos=command.find('Sethigh=') #Sethigh= giá trị 1, giá trị 2…
                          change=False
                          if(pos!=-1):
                              data=command.split('=')
                              if(len(data)==2):
                                  try:
                                      gethigh=""
                                      highs=data[1].split(",")
                                      print(highs)
                                      for i in range(len(highs)):
                                        if sim7600.is_float(highs[i]):
                                          print(float(highs[i]))
                                          Config.highset[i]=float(highs[i])
                                          
                                          change=True
                                          gethigh += str(Config.highset[i])+ ","
                                      if change:
                                          thingresponse +=" Gethigh="
                                          thingresponse += gethigh
                                  except Exception as e:
                                      thingresponse='Error Sethigh:'+str(e)
                                  print("Thingresponse:",thingresponse)
                          else:
                              pos=command.find('Setb=') #Calib=1,2,3,4
                              change=False
                              if(pos!=-1):
                                  data=command.split('=')
                                  if(len(data)==2):
                                      try:
                                          calibstr=""
                                          calibs=data[1].split(",")
                                          print(calibs)
                                          for i in range(len(calibs)):
                                            if sim7600.is_float(calibs[i]):
                                              print(float(calibs[i]))
                                              Config.calibset[i]=float(calibs[i])
                                              change=True
                                              calibstr += str(Config.calibset[i])+ ","
                                          if change:
                                              thingresponse +=" Getb="
                                              thingresponse += calibstr
                                      except Exception as e:
                                          thingresponse='Error Setb:'+str(e)
                                      print("Thingresponse:",thingresponse)
                              else:
                                  pos=command.find('Seta=') #Seta=y=ax+b
                                  change=False
                                  if(pos!=-1):
                                      data=command.split('=')
                                      if(len(data)==2):
                                          try:
                                              calibstr=""
                                              calibs=data[1].split(",")
                                              print(calibs)
                                              for i in range(len(calibs)):
                                                if sim7600.is_float(calibs[i]):
                                                  print(float(calibs[i]))
                                                  Config.gainset[i]=float(calibs[i])
                                                  change=True
                                                  calibstr += str(Config.gainset[i])+ ","
                                              if change:
                                                  thingresponse +=" Geta="
                                                  thingresponse += calibstr
                                          except Exception as e:
                                              thingresponse='Error Seta:'+str(e)
                                          print("Thingresponse:",thingresponse)
                                          
                                  else:
                                      pos=command.find('Setinouts=') #Setinouts=10,20
                                      if(pos!=-1):
                                          data=command.split('=')
                                          if(len(data)==2):
                                              try:
                                                  inouts=data[1].split(",")
                                                  if(len(inouts)>=1):
                                                      inputs=int(inouts[0])
                                                      Config.alarm=inputs & 0x01
                                                      Config.sms=inputs>>1 & 0x01
                                                      change=True
                                                      #thingresponse+=" Getinouts="+str(data[1])
                                                      thingresponse+="Inputs:"+str((Config.sms<<1) + Config.alarm)
                                                    
                                              except Exception as e:
                                                  print('Error Setinputs:'+str(e))
                                      else:
                                          pos=command.find('Key=') #Key=id,apikey
                                          
                                          if(pos!=-1):
                                              data=command.split('=')
                                              print("Thing get status3:",data)
                                              if(len(data)==2):
                                                  try:
                                                      keys=data[1].split(",")
                                                      print("Thing get status4:",keys)
                                                      if(len(keys)==2):
                                                          if len(keys[0])>4 and len(keys[1])==16:
                                                              Config.thingid = keys[0]
                                                              Config.thingkey = keys[1]
                                                              change=True
                                                              thingresponse+="Cloud change successful!"
                                                          else:
                                                              thingresponse+="Wrong key length, correct length is 16 characters!"     
                                                  except Exception as e:
                                                      print('Error Cloud change:'+str(e))
                                          else:
                                                pos=command.find('Setupdate=') # Setupdate=id
                                                if(pos!=-1):
                                                    data=command.split('=')
                                                    if(len(data)==2):
                                                        if len(data[1])==6:
                                                            if sim7600.FTP_OTA():
                                                                thingresponse+="Software update successful!"
                                                                machine.reset()
                                                        
                                                    #thingresponse+="Software update failed!"
                                                          
        if(len(thingresponse)):
            Config.response_thing_status=thingresponse
            Config.Save_setting()
        
# Gắn thẻ SD vào hệ thống tập tin
sd_status=False
def mount_sd():
    global sd_status
    try:
        spi = SoftSPI(baudrate=200000, polarity=0, phase=0, sck=Pin(14), mosi=Pin(15), miso=Pin(2))
        sd = sdcard.SDCard(spi, machine.Pin(13))
        os.mount(sd, '/sd')
        files = os.listdir('/sd')
        print("SD Card:",files)
        sd_status=True
    except OSError as e:
        print("Error SD:", e)
        sd_status=False
#mount_sd()
# Tạo thư mục theo định dạng ngày tháng năm
def create_directory(dir_name):
    path = "/sd/" + dir_name
    print("Path:",path)
    names = os.listdir('/sd')
    if dir_name in names:
        return path
    else:
        os.mkdir(path)
    return path
# Ghi dữ liệu vào file
def write_data(path, namedevice, content):
    # Lấy thời gian hiện tại
    now = time.localtime()
    filename = "{}/{}_{:04d}{:02d}{:02d}{:02d}{:02d}00.txt".format(path, namedevice, now[0], now[1], now[2], now[3], now[4])
    #filename = f"{path}/{namedevice}_{now[0]}{now[1]}{now[2]}{now[3]}{now[4]}{now[5]}.txt" 
    with open(filename, 'w') as f:   
        f.write(content)

    print(f"Wrote data to file {filename}")
    return filename
    
# -------Bang dau chuong trinh------
sim7600.Start_gsm()
count_error=0
print(version+'\n')
sim7600.send_at_command('AT+CGPSINFOCFG=0,31',3)
while True:
    res=check_at()
    if res:
        print("\nConnected GSM!")
        break
    else:
        time.sleep(5)
        count_error+=1
        print(count_error)
    if count_error==10:
        print("Restart GSM")
        sim7600.Start_gsm()
    if count_error>20:
        print("Machine.reset()")
        sim7600.Stop_gsm()
        machine.reset()  # Khởi động lại ESP32

'''
response=Get_GPS()
if response is not None and len(response)==2:
    Config.gpslatlon=response
    if lcdconnect:
        strlcd=f'Lat: {response[0]} \nLon: {response[1]}'
        lcd.clear()
        lcd.putstr(strlcd)
else:
    Config.gpslatlon=None
'''
#beep()
try:
    sim7600.get_time()
    rtc_time = rtc.datetime()
    if rtc_time[0]<2024:
       sim7600.get_time()
    # Kiểm tra trạng thái SIM
    sim7600.check_sim_status()
    # Kiểm tra kết nối mạng
    sim7600.check_network_registration()
    # Kết nối đến mạng
    csq = sim7600.check_signal_quality()
    csqstr=f"GSM Strength: {csq}"
    #sim7600.delete_sms()
    #sim7600.FTP_OTA()
    if len(Config.thingid):
        datas=sim7600.get_info_thing(Config.thingid)
        if len(datas)>=5:
            Config.devicename=datas[0]
            Config.fieldname[0]=datas[1]
            Config.fieldname[1]=datas[2]
            Config.fieldname[2]=datas[3]
            Config.fieldname[3]=datas[4]
            Config.Save_setting()
            rtc_time = rtc.datetime()
            # Định dạng thời gian
            formatted_time = "Date: {:04}-{:02}-{:02}\nTime: {:02}:{:02}:{:02}".format(
                rtc_time[0], rtc_time[1], rtc_time[2],
                rtc_time[4], rtc_time[5], rtc_time[6]
            )
            if lcdconnect:
                lcd.clear()
                strlcd=Config.devicename+'\n'+formatted_time+'\n'+csqstr
                lcd.putstr(strlcd)
                print(strlcd)
                time.sleep_ms(10000)
except Exception as e:
    strlcd="Error get infor: "+str(e)
    print(strlcd)
    '''sim7600.log_error(strlcd)
    time.sleep_ms(10000)
    sim7600.Stop_gsm()
    machine.reset()'''
    
wdt.feed()
rtc_time = rtc.datetime()
last_minute =  rtc_time[5]
last_hour = rtc_time[4]
lcd_index=0
# Truyen cac thong so cai dat khi khoi dong lai
thingstatus=check_reset_reason()+ " Gettimeupload="+str(Config.tupload)
thingstatus+=" Getlow="
for i in range(len(Config.lowset)):
    thingstatus+=str(Config.lowset[i])+ ","
thingstatus+=" Gethigh="
for i in range(len(Config.highset)):
    thingstatus+=str(Config.highset[i])+ ","
thingstatus+=" Getphone="
for i in range(len(Config.tel)):
    thingstatus+=str(Config.tel[i])+ ","
thingstatus+=" Inputs:"+str((Config.sms<<1) + Config.alarm)
Config.response_thing_status = thingstatus + ' ' +version
print(Config.response_thing_status)
#beep()
while True:
    #led_blink()
    gc.collect()  # Giải phóng bộ nhớ
    try:
        vpower = round(((adcpow.read_uv()/1000000)*2),2)#round(adc.read_u16()/10000+0.4,1)
        vbat = round(((adcbat.read_uv()/1000000)*2),2)#round(adc.read_u16()/10000+0.4,1)
        print("Volt power/bat:",vpower,vbat)
        if RAIN:
            if last_hour!=rtc_time[4]:
                last_hour=rtc_time[4]
                hourly_count=0
                if last_hour==0:
                    daily_count=0
                save_rain_data(pulse_count, hourly_count, daily_count)
            Config.val[0]=round(pulse_count*Config.gainset[0]+Config.calibset[0],1)
            Config.val[1]=round(hourly_count*Config.gainset[1]+Config.calibset[1],1)
            Config.val[2]=round(daily_count*Config.gainset[2]+Config.calibset[2],1)
            Config.val[3]=round(vpower+Config.calibset[3],1)
            # Kiểm tra thời gian từ xung cuối cùng
            current_time = time.ticks_ms()
        elif Ultrasonic:
            distance1 = measure_distance(14,15)
            distance2 = measure_distance(2,35) 
            distance3 = measure_distance(32,34)
            if distance1<200:
                val1=round(15-distance1+Config.calibset[0],1)
                if val1>0:
                    Config.val[0]=val1
            if distance2<200:
                val2=round(15-distance2+Config.calibset[1],1)
                if val2>0:
                    Config.val[1]=val2
            if distance3<200:
                val3=round(15-distance3+Config.calibset[2],1)
                if val3>0:
                    Config.val[2]=val3
            Config.val[3]=round(vbat+Config.calibset[3],1)
        elif SDS011:
            print('Start fan for 5 seconds.')
            dust_sensor.wake()
            time.sleep(5)
            #Returns NOK if no measurement found in reasonable time
            status = dust_sensor.read()
            #Returns NOK if checksum failed
            pkt_status = dust_sensor.packet_status
            #Stop fan
            dust_sensor.sleep()
            if(status == False):
                print('Measurement failed.')
            elif(pkt_status == False):
                print('Received corrupted data.')
            else:
                print('PM25: ', dust_sensor.pm25)
                print('PM10: ', dust_sensor.pm10)
                Config.val[0]=round(dust_sensor.pm25+Config.calibset[0],2)
                Config.val[1]=round(dust_sensor.pm10+Config.calibset[1],2)
            try:
                temperature, humidity = sensor_sht30.measure()
                print('Temperature:', temperature, 'ºC, RH:', humidity, '%')
                Config.val[2]=round(temperature+Config.calibset[2],1)
                Config.val[3]=round(humidity+Config.calibset[3],1)
            except Exception as e:
                strlcd="Error FAS-SHT30: "+str(e)
                print(strlcd)
                time.sleep(1)
        else:
            if TH:
                timeoutsht30=time.time()
                while True:
                    if time.time()-timeoutsht30>20:
                        #Config.val[0]=0
                        #Config.val[1]=0
                        Config.sensorstatus[0]=2
                        Config.sensorstatus[1]=2
                        break
                    try:
                        temperature, humidity = sensor_sht30.measure()
                        print('Temperature:', temperature, 'ºC, RH:', humidity, '%')
                        Config.val[0]=round(temperature+Config.calibset[0],2)
                        Config.val[1]=round(humidity+Config.calibset[1],2)
                        break
                    except Exception as e:
                        strlcd="Error FAS-SHT30: "+str(e)
                        print(strlcd)
                        time.sleep(2)
                    
            else: 
                ds = ds18x20.DS18X20(ow)
                roms = ds.scan()
                ds.convert_temp()
                time.sleep_ms(750)
                for i, rom in enumerate(roms):
                    Config.val[i]=round(ds.read_temp(rom)+Config.calibset[i],2)
                    
            Config.val[2]=round(vpower+Config.calibset[2],2)
            Config.val[3]=round(vbat+Config.calibset[3],2)
        # Sau tupload phut thi lay thong tin cai dat va gui du lieu len thing
        rtc_time = rtc.datetime()
        if rtc_time[0]<2024:
           sim7600.get_time() 
        # Định dạng thời gian
        formatted_time = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
            rtc_time[0], rtc_time[1], rtc_time[2],
            rtc_time[4], rtc_time[5], rtc_time[6]
        )
        # Reset WDT để tránh khởi động lại
        wdt.feed()
        # Minute 
        if last_minute!=rtc_time[5]:
            last_minute=rtc_time[5]
            if Config.tdelaysms>0:
                Config.tdelaysms-=1
                print(Config.tdelaysms)
            # Kiem tra do am > 0
            if Config.tdelaysms==0 and Config.val[1]>0:
                Config.Alarm()              
            # ghi vao the nho SD
            if sd_status and rtc_time[5] % Config.tupload == 0:
                try:
                    if len(Config.ftp)>0:
                        content=''
                        now = time.localtime()
                        time_txt = "{:04d}{:02d}{:02d}{:02d}{:02d}00".format(now[0], now[1], now[2], now[3], now[4])
                        for i, val in enumerate(Config.val):
                            content+=Config.fieldname[i]+"\t"+str(Config.val[i])+"\t"+time_txt+"\t0"+str(Config.sensorstatus[i])+"\r\n"
                        print(content)
                        path = create_directory(Config.devicename)
                        print(path)
                        filename=write_data(path,Config.devicename,content) 
                        sim7600.FTPUpload(Config.ftp,Config.devicename,now[0],now[1],now[2],filename)
                    sim7600.log_to_csv(Config.fieldname, Config.val)
                except Exception as e:
                    print("Error SD and FTP:",str(e))
                    sd_status=False
                    
            if len(Config.thingid) and  (rtc_time[5] % Config.tupload ==0 or len(Config.alarmstr)>0 or len(Config.response_thing_status)>0):
                get_status_thing(Config.thingid)
                url = f'http://api.thingspeak.com/update?api_key={Config.thingkey}'
                fieldthing=''
                for i, val in enumerate(Config.val):
                    fieldthing=fieldthing+'&field'+str(i+1)+'='+str(val)
                  
                if len(Config.alarmstr):
                    #beep(0.5)
                    Config.response_thing_status+='\n'+Config.alarmstr

                '''if len(Config.response_thing_status)==0 and Config.gpslatlon is not None:
                    Config.response_thing_status='GPS: '+str(Config.gpslatlon[0])+','+str(Config.gpslatlon[1])'''
                    
                if len(Config.response_thing_status)>0:
                    Config.response_thing_status=sim7600.url_encode(Config.response_thing_status)
                    url = url + fieldthing +'&status='+Config.response_thing_status
                    Config.response_thing_status=""
                elif Config.gpslatlon is not None:
                    url = url + fieldthing + "&field5=" + str(Config.gpslatlon[0]) + "&field6=" + str(Config.gpslatlon[1])
                else:
                    url = url + fieldthing
                #print(url)
                # Kiem tra do am > 0
                #if Config.val[1]>0:
                response=sim7600.send_http_get(url)
                if len(response):
                    Config.report=f'Cloud quantity:{response}'
                '''if vbat>1 and vbat<3:
                    sim7600.Stop_gsm()
                    if lcdconnect:
                        lcd.backlight_off()
                    deepsleep(120*60000)  # Đi vào chế độ ngu 120p'''
        # in ra LCD
        if lcdconnect:
            lcd.clear()
            strlcd=''
            for i in range(len(Config.fieldname)-1):
                strsensor=Config.fieldname[i]+': '+str(Config.val[i])+'\n'
                strlcd+=strsensor[:20]
            if len(Config.report):
                strlcd+=Config.report[:20]
                Config.report = ''
            elif lcd_index==0:
                stralarm = 'on' if Config.alarm else 'off'
                strlcd+='CID:'+Config.thingid+' Alarm '+ stralarm
            elif lcd_index==1:
                stralarm = 'on' if Config.sms else 'off'
                strlcd+='CID:'+Config.thingid+' Sms: '+ stralarm
            elif lcd_index==2:
                stralarm = 'on' if Config.sms else 'off'
                strlcd+='WWW.FASFARTECH.VN'
            elif lcd_index==3:
                csq = sim7600.check_signal_quality()
                csqstr=f"GSM Strength: {csq}"
                strlcd+=csqstr
            elif lcd_index>=4:
                strsensor=Config.fieldname[-1]+': '+str(Config.val[-1])+'\n'
                strlcd+=strsensor[:20]
            else:
                strlcd+=formatted_time
            print(strlcd)
            lcd.putstr(strlcd)
            lcd_index+=1
            if lcd_index>5:
                lcd_index=0
        #time.sleep(100)
        #lcd.backlight_off()
        # Gui canh bao qua SMS
        if Config.tdelaysms==0:
            if len(Config.alarmstr):
                if Config.sms:
                    for tel in Config.tel:
                        if(len(tel)>3):
                            sim7600.make_call(tel)
                            time.sleep_ms(10000)
                            wdt.feed()
                            sim7600.hang_up()
                            time.sleep_ms(10000)
                            wdt.feed()
                            Config.report = sim7600.send_sms(tel,Config.devicename+"\n"+Config.alarmstr+"\nFASFARTECH")
                            time.sleep_ms(10000)
                            # Reset WDT để tránh khởi động lại
                            wdt.feed()
                    Config.tdelaysms=5
                Config.alarmstr=""
    except Exception as e:
        strlcd="Error loop: "+str(e)
        print(strlcd)
        sim7600.log_error(strlcd)
        sim7600.Stop_gsm()
        time.sleep_ms(10000)
        machine.reset()  # Khởi động lại ESP32
    
    ledpm25.scroll_text(f"PM25:{str(Config.val[0])} PM10:{str(Config.val[1])} TEMP:{str(Config.val[2])} HUMI:{str(Config.val[3])}")
    time.sleep_ms(200)
    '''
    phone, mess = sim7600.read_sms()
    if len(phone)>0 and len(mess)>0:
        for tel in Config.tel:
            if phone == tel:
                thingresponse=''
                if mess == 'Alarm on':
                    Config.alarm=1
                    thingresponse+="Inputs:"+str((Config.sms<<1) + Config.alarm)
                elif mess == 'Alarm off':
                    Config.alarm=0
                    thingresponse+="Inputs:"+str((Config.sms<<1) + Config.alarm)
                if len(thingresponse):
                    Config.response_thing_status=thingresponse
                    Config.Save_setting()'''
    if Config.sleepmode:
        print("Goto deep sleep !")
        sim7600.Stop_gsm()
        # put the device to sleep for 10*60000 phut
        deepsleep(Config.tupload*60000)

