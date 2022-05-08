from machine import Pin
import rp2


# Carrier frequency 38kHz
# Working frequency 380kHz, duty factor = 1/2
# Pulse when irq is cleared. Space when irq is set
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def led():
    irq(4)
    wrap_target()
    set(pins, 0)[3]
    wait(0, irq, 4)
    set(pins, 1)[4]
    wrap()


# Controller for IR transmitter led with NEC protocol
# Working frequenty 50kHz
# Data format:
# Protocol:
# -- Leader Code
# ---- Pulse:  9ms
# ---- Space:  4.5ms
# -- Address Code (16 bit)
# ---- Pulse:  560us
# ---- Space:  560us for bit 0, 1690us for bit 1
# -- Data Code (16 bit)
# ---- Pulse:  560us
# ---- Space:  560us for bit 0, 1690us for bit 1
# -- Stop Bit: 560us pulse
# -- Gap:      140ms space
@rp2.asm_pio(out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def nec_tx():
    wrap_target()
    pull()
    # Leader Code: Pulse 9ms = 20us * 25 * 18
    set(x, 17)
    irq(clear, 4)
    label('leader_pulse')
    jmp(x_dec, 'leader_pulse')[24]
    # Leader Code: Space 4.5ms = 20us * 25 * 9
    set(x, 8)
    irq(4)
    label('leader_space')
    jmp(x_dec, 'leader_space')[24]

    # Address Code and Data Code
    label('sending')
    # Pulse 560us = 20us * 28
    irq(clear, 4)
    out(x, 1)[26]
    # Space 560us = 20us * (26 + 1 + 1) include two jmps
    irq(4)[25]
    jmp(not_x, 'bit_zero')

    # Space 1690us - 560us = 1130us = 20us * 57 - 10us
    # ignore this 10 us because of frequency
    nop()[27]
    nop()[28]
    label('bit_zero')
    jmp(not_osre, 'sending')  # stop sending when osr is empty

    # Stop Bit: Pulse 560us = 20us * 28
    irq(clear, 4)[27]

    # Gap: Space 140ms = 20us * 28 * 5 * 25 * 2
    irq(4)
    set(x, 1)
    set(y, 24)
    label("gap")
    nop()[27]
    nop()[27]
    nop()[27]
    nop()[27]
    jmp(y_dec, "gap")[27]
    set(y, 24)
    jmp(x_dec, "gap")
    wrap()


class NECTransport:
    def __init__(self, pin=17):
        self.sm_led = rp2.StateMachine(0, led, freq=38_000 * 10, set_base=Pin(pin))
        self.sm_ctrl = rp2.StateMachine(1, nec_tx, freq=50_000, set_base=Pin(pin))
        self.active()

    def active(self):
        self.sm_led.active(1)
        self.sm_ctrl.active(1)

    def deactive(self):
        self.sm_led.active(0)
        self.sm_ctrl.active(0)

    def send(self, address, command):
        command_code = ((~command) << 8) + command if command <= 0xff else command
        address_code = ((~address) << 8) + address if address <= 0xff else address
        code = (command_code << 16) + address_code

        self.sm_ctrl.put(code)


if __name__ == '__main__':
    tx = NECTransport()
    tx.send(0x654c, 0x41)
