from PIL import Image
import os

# with Image.open('printout/sample.png') as im:
#     im.rotate(90, expand=True).show()

def print_out(filename, size, copy):
    """

    :param filename:
    :param size: '2x6', '4x6', '6x2', '6x4'
    :param copy:
    :return:
    """
    if size not in ['2x6', '4x6', '6x2', '6x4']:
        return False

    margin = 20
    with Image.open(filename) as origin:
        canvas = Image.new('RGBA', (1200 + margin*2, 1800 + margin*2), 'white')
        media = None

        if origin.width > origin.height:
            origin = origin.rotate(90, expand=True)

        if origin.width == 600:
            canvas.paste(origin, (margin+origin.width, margin))
            copy = int(copy / 2)
            media = '-div2'

        canvas.paste(origin, (margin, margin))
        filename_margined = f"{filename[:-4]}_margined.png"
        canvas.save(filename_margined, quailty=100)



        cmd = f"lp -d printer {filename_margined} -n {copy} -o PageSize={media}"
        print('$', cmd)
        # os.system(cmd)
        return True


print_out('printout/sample.png', '6x2', 2)
print_out('printout/2306071239_frame.png', '2x6', 2)
print_out('printout/test.png', '4x6', 2)
print_out('printout/test2.png', '6x4', 2)