
try:
    import loop_sds011
except Exception as e:
    print("Error loop:",str(e))
    import sim7600, machine, time
    sim7600.Start_gsm()
    sim7600.check_network_registration()
    while True:
        result = sim7600.FTP_OTA()
        if result:
            machine.reset()  # Khởi động lại ESP32
        time.sleep(50)
 