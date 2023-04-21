import aio_pika
import aiohttp
import asyncio
import os
import json
import datetime

user = os.environ.get('RABBITMQ_DEFAULT_USER', '')
pw = os.environ.get('RABBITMQ_DEFAULT_PASS', '')
host = os.environ.get('RABBITMQ_HOST', 'ampq://127.0.0.1:5672')
server = os.environ.get('PHOTOLOG_SERVER_HOST', 'http://127.0.0.1:8000')


async def receive_data(job_data: dict):
    job_url = f"{server}{job_data['job-id']}/"
    photo_url = f"{server}{job_data['photo-url']}/"
    copy = job_data['copy']

    # Download image
    async with aiohttp.ClientSession() as sess:
        async with sess.get(photo_url) as res:
            if not res.status == 200:
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
            os.system(f"lp -d printer {abs_filename} -n {copy}")
            #####

async def on_message(message: aio_pika.IncomingMessage):
    async with message.process() as msg:
        print(msg.body)
        print(msg.timestamp)
        data = json.loads(msg.body)
        try:
            data['job-id']
            data['photo-url']
            data['copy']
            await receive_data(data)
        except Exception as e:
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

    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
