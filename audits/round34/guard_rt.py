import asyncio, json, shutil
from playwright.async_api import async_playwright
W="/tmp/r34/new"; B="http://127.0.0.1:8795/embeds/ufc_334/"
async def state(pg, f):
    await pg.goto(B + f); await pg.wait_for_timeout(1500)
    return await pg.evaluate("(()=>{const e=document.getElementById('sean-proj');return e?[e.getAttribute('data-state'), e.textContent.includes('Line pending'), e.querySelectorAll('[data-id]').length]:null})()")
async def main():
    async with async_playwright() as p:
        br=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox"]); pg=await br.new_page(viewport={"width":390,"height":844})
        out=[]
        for label, live in (("live file has 0 pending (tonight)", "/tmp/r34/live_now.json"), ("a later publish holds fight 10 back", W + "/data/ufc_334_projections_pendingplant.json"), ("live file unreachable", None)):
            dst = W + "/data/ufc_334_projections.json"
            if live: shutil.copy(live, dst)
            else: shutil.move(dst, dst + ".off")
            r10, r9 = await state(pg, "fight_10.html"), await state(pg, "fight_09.html")
            if not live: shutil.move(dst + ".off", dst)
            out.append(f"{label}: fight 10 {r10} | fight 9 {r9}")
        shutil.copy("/tmp/r34/live_now.json", W + "/data/ufc_334_projections.json")
        print("\n".join(out)); await br.close()
asyncio.run(main())
