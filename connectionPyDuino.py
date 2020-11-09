import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect("192.168.1.119", "80")
s.send(b"GET / HTTP/1.1 \r\n\r\n")
a = s.recv(1024)
print(a)
