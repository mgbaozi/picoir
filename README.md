# Pico IR
IR Transmitter for Raspberry Pi Pico

## Supported Protocol
 - NEC

## Usage
Connect ir transmitter's data pin with pico's gpio 17
```python
from picoir.nec import NECTransport
tx = NECTransport(pin=17)
tx.send(0x654c, 0x41)
```