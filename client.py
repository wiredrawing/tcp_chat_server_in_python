import socket;
import threading;
import sys

BUFFER_SIZE = 16

# 実行時のコマンドライン引数からサーバー側のIPアドレスとポート番号を指定
arguments = sys.argv;
if len(arguments) < 3:
    print("Please specify the port number");
    exit();

# 分割代入
(server_host, server_port) = (arguments[1], int(arguments[2]));

# サーバー側のソケットを作成
client = socket.socket();
client.connect((server_host, server_port));


# サーバー側からメッセージを受信する
def read_packets_from_server(__client):
    while True:
        packets = b"";
        while True:
            data = __client.recv(BUFFER_SIZE);
            packets += data;
            if len(data) < BUFFER_SIZE:
                break;
        print(packets.decode("utf-8"))


# サーバー側にメッセージを送信する
def send_packets_to_server(__client):
    while True:
        temp = input(">> ");
        if len(temp) > 0:
            __client.send(temp.encode("utf-8"));


# スレッドの作成
read_thread = threading.Thread(target=read_packets_from_server, args=(client,));
send_thread = threading.Thread(target=send_packets_to_server, args=(client,));
send_thread.start();
read_thread.start()