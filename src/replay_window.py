class ReplayWindow:

    def __init__(self, window_size: int = 64):
        self.window_size = window_size
        self.top    = 0
        self.bitmap = 0

    def check_and_update(self, sn: int) -> bool:

        if sn > self.top:

            shift = sn - self.top
            if shift < self.window_size:

                self.bitmap = (self.bitmap << shift) | 1
            else:

                self.bitmap = 1
            self.top = sn
            return True

        diff = self.top - sn
        if diff >= self.window_size:

            return False

        bit = 1 << diff
        if self.bitmap & bit:

            return False

        self.bitmap |= bit
        return True

    def check_only(self, sn: int) -> bool:

        if sn > self.top:
            return True
        diff = self.top - sn
        if diff >= self.window_size:
            return False
        bit = 1 << diff
        return not bool(self.bitmap & bit)

    def reset(self):

        self.top    = 0
        self.bitmap = 0

    def __repr__(self):
        return (f"ReplayWindow(window_size={self.window_size}, "
                f"top={self.top}, bitmap={self.bitmap:#066b})")
