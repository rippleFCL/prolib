from typing import Union
import netifaces
import socket
import struct
import select
import zipfile
from socket import error as SocketError
from collections import deque

# errors


class dataToLong(Exception):
    pass


class unsupportedType(ValueError):
    pass


class messageSocket(socket.socket, object):
    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, fileno=None):
        self.buffered_data = b''
        super().__init__(family, type, proto, fileno)

    @classmethod
    def copy(cls, sock):
        fd = socket.dup(sock.fileno())
        copy = cls(sock.family, sock.type, sock.proto, fileno=fd)
        copy.settimeout(sock.gettimeout())
        return copy

    def send(self, data: Union[bytes, str]):
        """
        send: 

        Args:
            data (Union[bytes, str]): data to be sent

        Raises:
            dataToLong: raised if the data length exceeds unsigned long long 
            unsupportedType: raised if the data type is bytes or a string
        """
        try:
            data_length = struct.pack('Q', len(data))
        except struct.error:
            raise dataToLong()
        if type(data) is bytes:
            data = data_length + data
        elif type(data) is str:
            data = data_length + data.encode('utf-8')
        else:
            raise unsupportedType('data must be of type bytes or str')

        super().sendall(data)

    def sendall(self, data):
        self.send(data)

    def recv(self, recv_size):
        if super().getblocking():
            msg_length = b''
            while len(msg_length) < 8:
                self.buffered_data += super().recv(recv_size)
                read_length = 8-len(msg_length)
                msg_length += self.buffered_data[
                    :read_length
                ]
                self.buffered_data = self.buffered_data[read_length:]

            msg_length = struct.unpack('Q', msg_length)[0]

            while len(self.buffered_data) < msg_length:
                self.buffered_data += super().recv(recv_size)

            full_msg = self.buffered_data[:msg_length]
            self.buffered_data = self.buffered_data[msg_length:]
            return full_msg

    def accept(self):
        sock, conn_info = super().accept()
        return messageSocket.copy(sock), conn_info
