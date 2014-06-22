from serverconnection import ServerConnection

c = ServerConnection("localhost", 8082)
c.connect()
c.submit_results("sample", "Helloworld.txt")
c.disconnect()