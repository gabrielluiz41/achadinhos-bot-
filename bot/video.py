"""Vídeo vertical 1080x1920 (H.264 + AAC) a partir da capa e do cartão final.

Locução opcional com edge-tts (voz pt-BR). Sem TTS, o vídeo sai com trilha muda.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess

VOZ = os.getenv("TTS_VOZ", "pt-BR-FranciscaNeural")


def roteiro(gancho: str, titulo_curto: str, preco_txt: str) -> str:
    preco_fala = preco_txt.replace("R$ ", "") + " reais"
    return f"{gancho}. {titulo_curto}, por {preco_fala}. Achei, e é barato! Link na bio."


def locucao(texto: str, destino: str) -> bool:
    if os.getenv("TTS", "1") != "1":
        return False
    try:
        import edge_tts  # type: ignore
    except ImportError:
        return False
    try:
        asyncio.run(asyncio.wait_for(edge_tts.Communicate(texto, VOZ, rate="+12%").save(destino), 60))
        return os.path.getsize(destino) > 1000
    except Exception:
        return False


def duracao(arquivo: str) -> float:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", arquivo], capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except Exception:
        return 0.0


def gerar_video(capa: str, final: str, destino: str, audio: str | None = None) -> str:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg não encontrado")
    total = max(9.0, (duracao(audio) + 0.6) if audio else 0)
    t_final = 3.0
    t_capa = total - t_final + 0.5  # 0,5 s de transição
    fps = 30
    n = int(t_capa * fps)
    filtro = (
        f"[0:v]scale=1188:2112,zoompan=z='min(1+0.0009*on,1.08)':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps={fps},setsar=1,format=yuv420p[a];"
        f"[1:v]scale=1080:1920,fps={fps},setsar=1,format=yuv420p[b];"
        f"[a][b]xfade=transition=slideup:duration=0.5:offset={t_capa - 0.5:.2f}[v]"
    )
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-loop", "1", "-t", f"{t_capa:.2f}", "-i", capa,
           "-loop", "1", "-t", f"{t_final:.2f}", "-i", final]
    if audio:
        cmd += ["-i", audio]
    else:
        cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-filter_complex", filtro, "-map", "[v]", "-map", "2:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-t", f"{total:.2f}", "-movflags", "+faststart", destino]
    subprocess.run(cmd, check=True)
    return destino
