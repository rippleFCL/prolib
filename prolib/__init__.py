import os
import threading
import netifaces
import socket
import pickle


def get_ip():
    interfaces = netifaces.interfaces()
    for i in interfaces:
        addrs = netifaces.ifaddresses(
            i)
        try:
            HOST = addrs[netifaces.AF_INET][0]["addr"]
            if "192" in HOST or "172" in "HOST":
                break
        except:
            pass
    else:
        return "localhost"
    return HOST


class socket_wrapper:
    def __init__(self, conn):
        self.conn = conn

    def __recv_loop(self, num):
        data = ""
        while 1:
            try:
                data = self.conn.recv(
                    num)
                break
            except:
                pass
        return data

    def hand_shake_send(self):
        self.__recv_loop(
            4)
        self.conn.sendall(
            b"conf")
        self.__recv_loop(
            4)

    def hand_shake_recv(self):
        self.conn.sendall(
            b"conf")
        self.__recv_loop(
            4)
        self.conn.sendall(
            b"conf")

    def send(self, data, raw_bytes=False):
        self.hand_shake_send()
        self.conn.sendall(bytes(
            str(len(data)), "utf-8"))
        self.hand_shake_send()
        if raw_bytes:
            self.conn.sendall(
                data)
        else:
            self.conn.sendall(
                bytes(data, "utf-8"))

        self.hand_shake_send()

    def recv(self, recv_len=1024, raw_bytes=False):
        self.hand_shake_recv()
        length = self.__recv_loop(
            1024)
        real_length = int(
            length)
        self.hand_shake_recv()
        if raw_bytes:
            data_comp = b""
        else:
            data_comp = ""
        while len(data_comp) < real_length:
            if raw_bytes:
                data_comp += self.__recv_loop(
                    recv_len)
            else:
                data_comp += self.__recv_loop(
                    recv_len).decode()
        self.hand_shake_recv()
        return data_comp

    def send_var_dump(self, *args):
        self.send(pickle.dumps(
            args), raw_bytes=True)

    def recv_var_dump(self):
        data_list = pickle.loads(
            self.recv(1024*20, raw_bytes=True))
        return data_list

    def close(self):
        self.conn.close()


class ftp(socket_wrapper):
    def __init__(self, ip="", server=False, localhost=False):
        # saves ip for when closing
        self.ip = ip
        if server:  # starts socket server
            s = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            if not localhost:
                host = get_ip()
            else:
                host = "localhost"
            s.bind(
                (host, 5454))
            self.socket = s
        else:  # connects to socket server
            s = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            s.connect(
                (ip, 5454))
            self.conn = socket_wrapper(
                s)
            # needed for closing later
            self.conn.send(
                "keepalive")

    def send_file(self, end_file_dir, start_file_dir):
        self.conn.send(
            "ftp_file")
        self.conn.send(
            end_file_dir)
        with open(start_file_dir, "rb") as d:
            # reads all the bytes
            data = d.read()
            # sends all the bytes as bytes
            self.conn.send(
                data, raw_bytes=True)

    def send_folder(self, start_dir, end_dir="", start_dir_name_in_target_folder=""):
        file_to_walk = start_dir
        self.conn.send(
            "ftp_folder")

        if end_dir != "":
            self.conn.send(
                end_dir)
        else:
            self.conn.send(
                "none")

        if start_dir_name_in_target_folder != "":
            self.conn.send(
                start_dir_name_in_target_folder)
            self.conn.send(
                start_dir)
        else:
            self.conn.send(
                "none")

        dir_struct = []

        start_dir = start_dir.replace(
            "\\", "/")
        start_dir = (
            "/".join(start_dir.split("/")[:-1]))

        for dir, file, dirs in os.walk(file_to_walk):
            dir = dir.replace(
                "\\", "/").replace(start_dir.replace("\\", "/"), "")
            dir_struct.append(
                [dir, file, dirs])
        self.conn.send(
            str(dir_struct))
        directory = "start"
        while 1:
            bace_dir = self.conn.recv(
                2028)
            directory = (bace_dir.replace(
                end_dir, start_dir))
            if ":**<>*" in directory:
                break
            with open(directory, "rb") as stream:
                data_stream = stream.read()
                self.conn.send(
                    data_stream, raw_bytes=True)

    def recv_folder(self, conn):
        file_directory = conn.recv(
            1024)
        file_name = conn.recv()
        if file_name != "none":
            sorce_file_name = conn.recv()

        print(
            file_name, file_directory)
        if file_directory == "none":
            file_directory = ""
        else:
            comp_file_name = ""
            for i in file_directory.replace("\\", "/").split("/"):
                try:
                    comp_file_name += i+"/"
                    os.mkdir(
                        comp_file_name)
                except:
                    pass

        eval_data = conn.recv(
            1024)
        file_struct = eval(
            eval_data)

        for dir, _, files in file_struct:
            target_str = b"\\".decode()
            dir = file_directory + \
                dir.replace(
                    target_str, "/")
            file_dir_to_write = dir
            if file_name != "none":
                file_dir_to_write = file_dir_to_write.replace(
                    file_directory +
                    sorce_file_name, file_directory +
                    file_name
                )
            print(
                file_dir_to_write)
            try:
                os.mkdir(
                    file_dir_to_write)
            except:
                pass
            for i in files:
                with open(f"{file_dir_to_write}/{i}", "wb") as d:
                    conn.send(
                        f"{dir}/{i}")
                    d.write(conn.recv(
                        1024*1024*10, raw_bytes=True))
        conn.send(
            ":**<>*")

    def recv_file(self, conn):
        file_name = conn.recv(
            1024)
        data_in = conn.recv(
            1024*1024*10, raw_bytes=True)
        with open(file_name, "wb") as update:
            update.write(
                data_in)

    def start_threaded_ftp_server(self):
        x = threading.Thread(
            target=self.__listen_for_conn)
        x.start()

    def __listen_for_conn(self):
        while 1:
            print(
                "ftp server starting")
            self.socket.listen()
            conn, ip = self.socket.accept()
            conn = socket_wrapper(
                conn)
            if conn.recv() == "close":
                break
            else:
                x = threading.Thread(
                    target=self.__recv_data, args=(conn,))
                x.start()

    def __recv_data(self, conn):
        while 1:
            ftp_type = conn.recv(
                1024)
            if ftp_type == "ftp_folder":
                self.recv_folder(
                    conn)
            if ftp_type == "ftp_file":
                self.recv_file(
                    conn)
            if ftp_type == "close":
                while 1:
                    if conn.conn.recv(1024) == b"":
                        return 0

    def close_connection(self):
        print(
            "closing ftp conn")
        # closes inner thread
        self.conn.send(
            "close")
        self.conn.conn.close()

        # closes outer thread
        print(
            "closed ftp connection")
