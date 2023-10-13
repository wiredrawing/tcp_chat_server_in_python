import socket;
import threading;
import json

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

    # 指定バイト数分ずつ読み込んで,Socketからパケットを取得する
    @staticmethod
    def read_packets(client) -> str:
        packets = b"";
        while True:
            data = client.recv(BUFFER_SIZE)
            packets += data;
            if len(data) < BUFFER_SIZE:
                break
        # client socketからの戻り値は bytes型なのでstr型に変換する
        decoded_packets = packets.decode("utf-8");
        return decoded_packets

    def handler(self, client, client_key):

        while True:
            # clientへwelcomeメッセージを送信する
            client.send(bytes("\r\n最初にあなたの名前を入力して下さい", encoding="utf-8"));
            # clientからの入力を受け取る
            user_name = TCPServer.read_packets(client)
            # 入力内容が空でない場合
            if len(user_name) > 0:
                question_message = "あなたの名前は[{}]ですか?  <yes or no>".format(user_name);
                print(question_message);
                client.send(bytes(question_message, encoding="utf-8"))
                # yes or noの入力を受け取る
                answer = TCPServer.read_packets(client);
                print("受け取った回答[{}]".format(answer))
                if answer == "yes":
                    print("ユーザー名を確定しました");
                    break;

        # clientのユーザー名を一旦出力
        print("接続したユーザー名は[{}]です".format(user_name));
        client.send(bytes("[{}]さん,TCPサーバーへようこそ".format(user_name), encoding="utf-8"));

        # 当該ユーザーが他ユーザーにログインしたことを通知する
        # Socketからの初回メッセージの場合は
        # 取得したメッセージをユーザー名として扱う
        if not self.__accepted_user_names.get(client_key):
            self.__accepted_user_names[client_key] = user_name;

        self.broadcast_message(client_key, "[{}]さんが入室しました".format(user_name))

        while True:
            # 小分けにして受け取ったパケットを結合するため
            packets = TCPServer.read_packets(client);
            self.broadcast_message(client_key, packets);

    # 特定のユーザーの発言を他のユーザーにブロードキャストする
    def broadcast_message(self, client_key, packets):
        print("broadcast_message スタート");
        print(self.__accepted_sockets);
        for key in list(self.__accepted_sockets):
            # 自分のSocketクライアントにはメッセージを送信しない
            if key == client_key:
                continue;
            # 自分以外のSocketクライアントにメッセージを送信する
            user_name = self.__accepted_user_names[client_key];

            # パケットは\r\n(改行)区切りで送信する
            # 偶数行は発信者名,奇数行は発言内容とする
            packets = "{}\r\n{}\r\n".format(user_name, packets);
            try:
                self.__accepted_sockets[key].send(bytes(packets, encoding="utf-8"));
            except Exception as e:
                print(e);
                # 接続済み配列から現ループのkeyを削除する
                del self.__accepted_sockets[key];
                del self.__accepted_user_names[key];




tcp_server = TCPServer(server_host, server_port, server_backlog)
tcp_server.make_server();

tcp_server.run_server()
