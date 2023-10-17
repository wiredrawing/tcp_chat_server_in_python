import socket;
import threading;
import sys

import select


# 配列を指定数分に分割する
def split_list(target, number):
    """
    配列を指定数分に分割
    :param target:
    :param number:
    :return:
    """
    for index in range(0, len(target), number):
        yield target[index:index + number]


# サーバー側からメッセージを受信する
def read_packets_from_server(_client_):
    while True:
        packets = b"";
        number = select.select([_client_], [], [], 1);
        read_list = number[0];
        # 自身のソケットが読み込み可能な場合のみ処理を実行する
        for read in read_list:
            while True:
                try:
                    read.setblocking(False)
                    data = read.recv(BUFFER_SIZE)
                    # print(data);
                    # print(len(data))
                    packets += data;
                    if len(data) == 0:
                        break;
                    if len(data) < BUFFER_SIZE:
                        break
                except Exception as e:
                    print(type(e))
                    # ノンブロッキングの場合は例外がスローされるため
                    # 例外発生時 == 読み込み完了とする
                    if len(packets) > 0:
                        break;

            # データ受信時以外はノンブロッキングを解除する
            read.setblocking(True)
        if len(packets) > 0:
            # 受信したパケットは\r\n文字で分割する
            packets = packets.decode("utf-8").split("\r\n");
            packets = list(split_list(packets, 2));
            for index, value in enumerate(packets):
                for innder_index, innder_value in enumerate(value):
                    print(innder_value);


# サーバー側にメッセージを送信する
def send_packets_to_server(__client):
    while True:
        temp = input(">> ");
        if len(temp) > 0:
            __client.send(temp.encode("utf-8"));


if __name__ == "__main__":
    BUFFER_SIZE = 16

    # 実行時のコマンドライン引数からサーバー側のIPアドレスとポート番号を指定
    arguments = sys.argv;
    if len(arguments) < 2:
        server_host = "127.0.0.1"
        server_port = 11180
    else:

        # 分割代入
        (server_host, server_port) = (arguments[1], int(arguments[2]));

    # サーバー側のソケットを作成
    try:

        client = socket.socket();
        client.connect((server_host, server_port));
        # スレッドの作成
        read_thread = threading.Thread(target=read_packets_from_server, args=(client,));
        send_thread = threading.Thread(target=send_packets_to_server, args=(client,));
        send_thread.start();
        read_thread.start()
    except Exception as e:
        print(e);
