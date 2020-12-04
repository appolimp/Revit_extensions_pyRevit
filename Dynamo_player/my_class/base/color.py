import random


class ColorCoroutine(object):

    def __init__(self):
        self.data = ('##6C3483', '##F7DC6F', '##7FB3D5', '##76D7C4', '##148F77', '##E59866', '##BB8FCE', '##F1948A',
                     '##73C6B6', '##7DCEA0', '##D98880', '##239B56', '##117A65', '##A04000', '##283747', '##F8C471',
                     '##76448A', '##82E0AA', '##B7950B', '##B9770E', '##922B21', '##717D7E', '##B03A2E', '##AF601A',
                     '##1E8449', '##85C1E9', '##2874A6', '##85929E', '##1F618D', '##F0B27A', '##C39BD3', '##BFC9CA')

    def create_color(self):
        i = 0
        while i < len(self.data):
            yield self.data[i]
            i += 1

        while True:
            yield self.create_random_color()

    @staticmethod
    def create_random_color():
        return '##' + ''.join('{0:02x}'.format(random.randint(0, 255)) for _ in range(3)).upper()


if __name__ == '__main__':
    color = ColorCoroutine().create_color()
    print next(color)







