import socket
import random
import struct
import time

def create_udp_server(host, port, drop_rate):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    print(f"服务器监听：{host}:{port}, 丢包率: {drop_rate * 100}%")
    return server_socket

def parse_header(data):
    return struct.unpack("!IIII", data[:16]) #大端序 4*32位无符号整数

def make_header(flags, seq, ack, length):
    return struct.pack("!IIII", flags, seq, ack, length)

def handle_connection(server_socket):
    print("等待连接...")
    while True:
        data, addr = server_socket.recvfrom(1024)
        flags, seq, ack, length = parse_header(data)

        if flags == 1:  #SYN
            print(f"已从{addr}收到SYN")
            server_isn = 10000

            #SYN-ACK
            response = make_header(2, server_isn, seq + 1, 0)
            server_socket.sendto(response, addr)
            print(f"已向{addr}发送SYN-ACK")
            break

    while True:
        data, addr = server_socket.recvfrom(1024)
        flags, seq, ack, length = parse_header(data)

        if flags == 3 and ack == server_isn + 1:
            print(f"已与{addr}建立连接")
            return addr, server_isn

def handle_data_transfer(server_socket, client_addr, drop_rate):
    expected_seq = 0  # 期望的下一个序列号
    print("开始数据传输...")

    while True:
        data, addr = server_socket.recvfrom(1024)
        if addr != client_addr:
            continue

        flags, seq, ack, length = parse_header(data)

        if flags == 4:  # FIN
            print(f"从 {addr}收到FIN")
            #FIN-ACK
            fin_ack = make_header(5, 0, seq + 1, 0)
            server_socket.sendto(fin_ack, addr)
            print(f"已向{addr}发送FIN-ACK")
            break

        elif flags == 6:  # DATA
            payload = data[16:16 + length]
            print(f"收到数据：seq={seq}, 期望： {expected_seq}")

            # 随机丢包模拟
            if random.random() < drop_rate:
                print(f"随机丢包：seq={seq}")
                continue

            if seq == expected_seq:
                expected_seq += 1
                print(f"收到数据：seq={seq}, 新期望：{expected_seq}")

            #累积确认
            ack_pkt = make_header(7, 0, expected_seq, 0)
            server_socket.sendto(ack_pkt, addr)


def close_connection(server_socket):
    print("等待最终ACK...")
    try:
        data, addr = server_socket.recvfrom(1024)
        flags, seq, ack, length = parse_header(data)
        if flags == 3:
            print("连接关闭")
    finally:
        server_socket.close()


def main():
    HOST = "127.0.0.1"
    PORT = 12345
    DROP_RATE = 0.1

    server_socket = create_udp_server(HOST, PORT, DROP_RATE)

    try:
        client_addr, server_isn = handle_connection(server_socket)

        handle_data_transfer(server_socket, client_addr, DROP_RATE)

        close_connection(server_socket)
    except KeyboardInterrupt:
        print("\n用户关闭服务器")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()