from serverconnection import ServerConnection

c = ServerConnection()
c.connect()
c.submit_results("sample", "Helloworld.txt")
c.disconnect()