import socket;
import threading;

# クライアントからメッセージを受信するバイトサイズ
BUFFER_SIZE = 16
# TCPサーバーを起動する
server_host = "192.168.0.16"
server_port = 11180;
server_backlog = 256


# server = socket.socket()
# server.bind((server_host, server_port));
# server.listen(server_backlog)
# # 受付済みのクライアントSocketを保持
# accepted_sockets = {};
# # 受付済みSocketのホスト名とユーザー名を紐付ける
# accepted_user_names = {};


# # クライアントのSocketからメッセージを受信する
# def get_message_from_client(__socket, __key):
#     # メッセージの受信はクライアントが接続を切断するまで
#     while True:
#         whole_mesage = b"";
#         while True:
#             data = __socket.recv(BUFFER_SIZE);
#             whole_mesage += data;
#             if len(data) < BUFFER_SIZE:
#                 break;
#         connected_message = whole_mesage.decode("utf-8")
#         if len(connected_message) > 0:
#             # <exit>というメッセージの場合Socketをクローズする
#             if connected_message == "exit":
#                 __socket.close();
#                 break;
#             # メッセージが正しく入力された場合,その他の接続済みSocketにも
#             # メッセージを返却する
#             if not accepted_user_names.get(__key):
#                 # メッセージを修正
#                 connected_message = "[{}]さんが入室しました".format(connected_message);
#                 accepted_user_names[__key] = connected_message;
#
#             # 初回入力時のメッセージはクライアント名を入力したとする
#             for key, value in accepted_sockets.items():
#                 if key != __key:
#                     value.send(bytes(connected_message, encoding='utf-8'));
#                 else:
#                     print("送信者にも同様のメッセージを送信しました");
#
#             print(connected_message);
#     return false;


class TCPServer:

    def __init__(self, host, port, backlog):
        self.__server_host = host
        self.__server_port = port
        self.__backlog = backlog;
        # defaultでは設定しない
        self.__server = None;
        # 当該サーバーに接続して許可されたSocket一覧を保持
        self.__accepted_sockets = {};
        # クライアントごとのユーザー名を保持
        self.__accepted_user_names = {}

    def accepted_sockets(self):
        return self.__accepted_sockets;

    def accepted_user_names(self):
        return self.__accepted_user_names

    def make_server(self):
        s = socket.socket();
        s.bind((self.__server_host, self.__server_port))
        s.listen(self.__backlog);
        self.__server = s;
        # 一応listenまで行ったサーバーsocketを片脚する
        return self.__server

    def run_server(self):
        while True:
            print("[クライアントを受付中...]");
            (client, address) = self.__server.accept();
            client_key = "{}:{}".format(address[0], address[1])
            self.__accepted_sockets[client_key] = client
            # スレッドを新規作成して,メインスレッドのブロックを防ぐ
            receive_thread = threading.Thread(target=self.handler, args=(client, client_key))
            receive_thread.start();

    def handler(self, client, client_key):
        while True:
            # 小分けにして受け取ったパケットを結合するため
            packets = b"";
            while True:
                data = client.recv(BUFFER_SIZE)
                packets += data;
                # 読み取ったパケットサイズが指定サイズより小さい場合
                # SocketのEOFとする
                if len(data) < BUFFER_SIZE:
                    break;

            # Socketから受信したデータはバイト列なのでstr型に変換する
            packets = packets.decode("utf-8");
            # Socketからの初回メッセージの場合は
            # 取得したメッセージをユーザー名として扱う
            if not self.__accepted_user_names.get(client_key):
                self.__accepted_user_names[client_key] = packets
                packets = "[{}]さんが入室しました".format(packets)

            for key, value in self.__accepted_sockets.items():
                if key == client_key:
                    continue;
                # 自分以外のSocketクライアントにメッセージを送信する
                user_name = self.__accepted_user_names[client_key];
                broadcasted_packets = "[{}]:{}".format(user_name, packets, );
                value.send(bytes(broadcasted_packets, encoding="utf-8"));


tcp_server = TCPServer(server_host, server_port, server_backlog)
tcp_server.make_server();

tcp_server.run_server()
