import asyncio, threading, time

LOOP = None

async def do_async(name):
    print("start", name)
    await asyncio.sleep(1)
    print("done", name)

def start_job(*_):
    # called from another thread; post onto loop
    LOOP.call_soon_threadsafe(lambda: LOOP.create_task(do_async("job")))

def run_loop():
    global LOOP
    LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(LOOP)
    LOOP.call_soon(lambda: LOOP.create_task(do_async("auto-start"))) # auto-start
    LOOP.run_forever()

# run the loop in main thread
threading.Thread(target=run_loop, daemon=True).start()

# later, from some other thread (like pystray), schedule a job:
time.sleep(0.2)
start_job()
