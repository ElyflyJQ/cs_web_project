import socket
import struct
import time
import sys
import pandas as pd
import random

client_socket = None
server_addr = None
window_size = 400
packet_size = 80
packets_per_window = 5
client_isn = 10000
seq_num = 0
base = 0 #窗口左边界
next_seq = 0
packets = []
sent_times = {}
ack_received = {}
rtt_list = []
total_packets = 30
transmissions = 0

def make_header(flags, seq, ack, length):
    return struct.pack("!IIII", flags, seq, ack, length)

def parse_header(data):
    return struct.unpack("!IIII", data[:16])

def send_packet(seq, payload):
    global transmissions
    flags = 6  # DATA
    header = make_header(flags, seq, 0, len(payload))
    packet = header + payload
    client_socket.sendto(packet, server_addr)

    start_byte = seq * packet_size
    end_byte = start_byte + len(payload) - 1

    print(f"已发送包： {seq} ({start_byte}~{end_byte})\n")
    sent_times[seq] = time.time()
    transmissions += 1

def send_fin():
    header = make_header(4, total_packets, 0, 0)
    client_socket.sendto(header, server_addr)
    print("已发送FIN")

def establish_connection():
    global client_socket, server_addr

    #第一次握手
    syn_header = make_header(1, client_isn, 0, 0)
    client_socket.sendto(syn_header, server_addr)
    print("已发送SYN")

    #第二次握手
    while True:
        client_socket.settimeout(3.0)
        try:
            data, addr = client_socket.recvfrom(1024)
            flags, seq, ack, length = parse_header(data)

            if flags == 2 and ack == client_isn + 1:
                print("已收到 SYN-ACK\n")
                break

        except socket.timeout:
            print("超时重传SYN\n")
            client_socket.sendto(syn_header, server_addr)

    #第三次握手
    ack_header = make_header(3, client_isn + 1, seq + 1, 0)
    client_socket.sendto(ack_header, server_addr)
    print("已建立连接\n")

def generate_packets():
    global packets
    for i in range(total_packets):
        payload = bytes([i] * packet_size)#发送80字节大小的数据
        packets.append(payload)

def send_window():
    global next_seq
    while next_seq < min(base + packets_per_window, total_packets):
        if next_seq not in sent_times or sent_times[next_seq] == 0:
            send_packet(next_seq, packets[next_seq])
        next_seq += 1

def wait_for_acks():
    global base, rtt_list
    timeout = 0.3
    start_time = time.time()

    while time.time() - start_time < timeout:
        client_socket.settimeout(timeout - (time.time() - start_time))#动态调整超时时间
        try:
            data, addr = client_socket.recvfrom(1024)
            flags, seq, ack, length = parse_header(data)

            if flags == 7 and ack>base:
                print(f"收到ACK：{ack}")
                for s in range(base, ack):
                    if s in sent_times and s not in ack_received:
                        rtt = (time.time() - sent_times[s]) * 1000
                        rtt_list.append(rtt)
                        ack_received[s] = True
                        start_byte = s * packet_size
                        end_byte = start_byte + packet_size - 1
                        print(f"Packet {s} ({start_byte}~{end_byte}) 已确认, RTT={rtt:.2f}ms\n")
                base = ack#滑动窗口
                return True
        except socket.timeout:
            break
    return False

def close_connection():
    send_fin()

    while True:
        client_socket.settimeout(3.0)
        try:
            data, addr = client_socket.recvfrom(1024)
            flags, seq, ack, length = parse_header(data)
            if flags == 5:  # FIN-ACK
                print("已收到FIN-ACK\n")
                break
        except socket.timeout:
            print("超时重传FIN\n")
            send_fin()

    ack_header = make_header(3, total_packets + 1, ack, 0)
    client_socket.sendto(ack_header, server_addr)
    print("连接关闭\n")

def print_statistics():
    loss_rate = (1 - total_packets / transmissions) * 100

    if rtt_list:
        rtt_series = pd.Series(rtt_list)
        stats = {
            "max_rtt": rtt_series.max(),
            "min_rtt": rtt_series.min(),
            "mean_rtt": rtt_series.mean(),
            "std_rtt": rtt_series.std()
        }
    else:
        stats = {"max_rtt": 0, "min_rtt": 0, "mean_rtt": 0, "std_rtt": 0}

    print("\n数据统计\n")

    print(f"丢包率: {loss_rate:.2f}%")
    print(f"最大RTT: {stats['max_rtt']:.2f}ms")
    print(f"最小RTT: {stats['min_rtt']:.2f}ms")
    print(f"平均RTT: {stats['mean_rtt']:.2f}ms")
    print(f"RTT标准差: {stats['std_rtt']:.2f}ms")

def run_client(server_ip, server_port):
    global client_socket, server_addr
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_addr = (server_ip, server_port)
    print(f"已与 {server_ip}:{server_port}建立连接, 窗口大小：{window_size} bytes")

    establish_connection()#执行三次握手

    generate_packets()

    while base < total_packets:
        send_window()
        if not wait_for_acks():
            print(f"超时，从{base}开始重传\n")
            next_seq = base
            for s in range(base, min(base + packets_per_window, total_packets)):#发送当前窗口内的包
                if s in sent_times:
                    start_byte = s * packet_size
                    end_byte = start_byte + packet_size - 1
                    print(f"重新发送packet {s} ({start_byte}~{end_byte})\n    ")
                    send_packet(s, packets[s])

    close_connection()
    print_statistics()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("请使用以下格式运行代码：<server_ip> <server_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    run_client(server_ip, server_port)