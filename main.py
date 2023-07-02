import aio_pika
import aiohttp
import asyncio
import os
import json
import datetime
from PIL import Image

user = os.environ.get('RABBITMQ_DEFAULT_USER', '')
pw = os.environ.get('RABBITMQ_DEFAULT_PASS', '')
host = os.environ.get('RABBITMQ_HOST', '127.0.0.1:5672')
server = os.environ.get('PHOTOLOG_SERVER_HOST', '')


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


async def receive_data(job_data: dict):
    job_url = f"{server}{job_data['job-id']}/"
    photo_url = f"{server}{job_data['photo-url']}/"
    copy = job_data.get('copy', 1)
    size = job_data.get('size', None)
    if not size:
        print('no size')
        return

    # Download image
    async with aiohttp.ClientSession() as sess:
        async with sess.get(photo_url) as res:
            if not res.status == 200:
                print('download failed')
                return  # Download failed

            # Save the image.
            filename = res.content_disposition.filename
            abs_filename = f"printout/{filename}"
            with open(abs_filename, 'wb') as f:
                while True:
                    # 1024*1024 = 1_048_576
                    chunk = await res.content.read(10485576)
                    if not chunk:
                        break
                    f.write(chunk)

            # Acknowledge for receiving to server
            async with aiohttp.ClientSession() as sess:
                async with sess.get(job_url) as res:
                    is_published = True if res.status == 200 else False

                    #####
                    # TODO: After downloading file
                    print_out(filename, size, copy)
                    #####

async def on_message(message: aio_pika.IncomingMessage):
    async with message.process() as msg:
        print(msg.timestamp, msg.body)
        data = json.loads(msg.body)
        try:
            data['job-id']
            data['photo-url']
            data['copy']
            data['size']
            await receive_data(data)
        except Exception as e:
            print('message error', e)
            pass


async def main():
    conn: aio_pika.RobustConnection = await aio_pika.connect_robust(
        url=f"amqp://{user}:{pw}@{host}/%2F",
        client_properties={'connected_user_id': user},
    )

    async with conn.channel() as channel:
        q = await channel.get_queue(user)

        # TODO: spin-lock
        while True:
            await q.consume(on_message)
            await asyncio.sleep(1)

    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
