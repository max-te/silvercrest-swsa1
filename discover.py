from dataclasses import dataclass
import enum
import socket
import asyncio
from abc import ABC, abstractmethod
from typing import ClassVar, override
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SEARCH_ALL_DATAGRAM = b"\x23\xff\xff\xff\xff\xff\xff\x02\x02"
BROADCAST_IP, PORT = ("255.255.255.255", 8530)

AES_KEY = b"0123456789abcdef"
AES_IV = b"0123456789abcdef"
aes = Cipher(
    algorithms.AES(AES_KEY),
    modes.CBC(AES_IV),
)


@dataclass
class Packet:
    number: int = 0xFFFF
    company: int = 0xC1
    device_type: int = 0x11
    auth_code: int = 0x7150
    payload: bytes = SEARCH_ALL_DATAGRAM

    def to_bytes(self) -> bytes:
        return (
            b"\x00"
            + self.number.to_bytes(2, "big")
            + self.company.to_bytes(1, "big")
            + self.device_type.to_bytes(1, "big")
            + self.auth_code.to_bytes(2, "big")
            + self.payload
        )

    @staticmethod
    def from_bytes(data: bytes) -> "Packet":
        return Packet(
            number=int.from_bytes(data[1:3], "big"),
            company=int.from_bytes(data[3:4], "big"),
            device_type=int.from_bytes(data[4:5], "big"),
            auth_code=int.from_bytes(data[5:7], "big"),
            payload=data[7:],
        )


class LockStatus(enum.IntEnum):
    OPEN = 0x40
    LOCKED = 0x44
    RESPONSE = 0x42


@dataclass
class Envelope:
    contents: Packet
    lock_status: LockStatus = LockStatus.OPEN
    mac: bytes = b"\xff\xff\xff\xff\xff\xff"

    def to_bytes(self) -> bytes:
        encryptor = aes.encryptor()
        contents = self.contents.to_bytes()
        encmsg = encryptor.update(contents) + encryptor.finalize()
        return (
            b"\x01"
            + self.lock_status.to_bytes(1, "big")
            + self.mac
            + len(encmsg).to_bytes(1, "big")
            + encmsg
        )

    @staticmethod
    def from_bytes(data: bytes) -> "Envelope":
        decryptor = aes.decryptor()
        response = decryptor.update(data[9:]) + decryptor.finalize()
        return Envelope(
            lock_status=LockStatus(int.from_bytes(data[1:2], "big")),
            mac=data[2:8],
            contents=Packet.from_bytes(response),
        )

    @staticmethod
    def for_command(data: bytes) -> "Envelope":
        return Envelope(
            contents=Packet(
                payload=data,
            ),
        )


class Response(ABC):
    PREFIX: ClassVar[int]

    @staticmethod
    def is_type(data: bytes) -> bool:
        return data[0] == Response.PREFIX

    @staticmethod
    @abstractmethod
    def from_bytes(data: bytes) -> "Response":
        pass


@dataclass
class SearchResponse(Response):
    ip: bytes
    mac: bytes
    key: bytes
    PREFIX: ClassVar[int] = 0x23

    @staticmethod
    @override
    def from_bytes(data: bytes) -> "SearchResponse":
        assert data[0] == SearchResponse.PREFIX
        ip = data[1:5]
        mac = data[5:11]
        keylen = data[11]
        key = data[12 : 12 + keylen]
        return SearchResponse(ip=ip, mac=mac, key=key)

    @override
    def __str__(self):
        ip = ".".join(map(str, self.ip))
        mac = ":".join(map("{:02x}".format, self.mac))
        return f"{ip} {mac} {self.key}"


class SilvercrestDiscoveryProtocol(asyncio.DatagramProtocol):
    responses: list[SearchResponse] = []

    @override
    def connection_made(self, transport: asyncio.transports.DatagramTransport):
        transport.sendto(
            Envelope.for_command(SEARCH_ALL_DATAGRAM).to_bytes(), (BROADCAST_IP, PORT)
        )

    @override
    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        try:
            envelope = Envelope.from_bytes(data)
            print(envelope)
            if envelope.lock_status == LockStatus.RESPONSE:
                if SearchResponse.is_type(envelope.contents.payload):
                    res = SearchResponse.from_bytes(envelope.contents.payload)
                    self.responses.append(res)
                    print(res, addr)
        except ValueError:
            return

    @override
    def error_received(self, exc: Exception):
        print("ERR", exc)


async def main():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        SilvercrestDiscoveryProtocol,
        family=socket.AF_INET,
        proto=socket.IPPROTO_UDP,
        allow_broadcast=True,
        local_addr=("0.0.0.0", PORT),
    )
    await asyncio.sleep(3)
    transport.close()
    print(protocol.responses)


asyncio.run(main())
