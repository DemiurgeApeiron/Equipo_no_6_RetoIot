import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("0.0.0.0", 80))
s.listen(1)
connection, remoteAddress = s.accept()

with connection:
    data = connection.recv(1024)
    print(data)
    connection.send(b"ok")
    connection.close()
    pass
