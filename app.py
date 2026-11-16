import asyncio
import os
import textwrap
import urllib.parse
import edge_tts
import gradio as gr
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
from PIL import Image, ImageDraw
import requests

CHARACTER_VOICES = {
    "Raju": ("hi-IN-MadhurNeural", "+15Hz"),
    "Rani": ("hi-IN-SwaraNeural", "+15Hz"),
    "Raja": ("hi-IN-MadhurNeural", "-10Hz"),
    "Dadi": ("hi-IN-SwaraNeural", "-8Hz"),
    "Narrator": ("hi-IN-MadhurNeural", "+0Hz"),
}


async def make_voice(text, char_name, out_path):
    voice, pitch = CHARACTER_VOICES.get(char_name, ("hi-IN-MadhurNeural", "+0Hz"))
    communicate = edge_tts.Communicate(text, voice, pitch=pitch)
    await communicate.save(out_path)


def make_cartoon_frame(dialogue, char_name, style, scene_num, out_img):
    prompt = f"{style}, {char_name} speaking in a vibrant cartoon scene, {dialogue}, expressive face, cinematic lighting, 8k"
    encoded = urllib.parse.quote(prompt)
    url = f"https://pollinations.ai{encoded}?width=1280&height=720&nologo=true&seed={scene_num+100}"

    try:
        res = requests.get(url, timeout=25)
        with open(out_img, "wb") as f:
            f.write(res.content)
        img = Image.open(out_img).convert("RGB")
    except Exception:
        img = Image.new("RGB", (1280, 720), color=(30, 58, 138))

    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle([(50, 530), (1230, 690)], fill=(10, 15, 30, 210))
    draw.rectangle([(65, 542), (240, 578)], fill=(225, 29, 72, 255))
    draw.text((85, 552), f"{char_name.upper()}", fill=(255, 255, 255))

    wrapped = textwrap.fill(dialogue, width=65)
    draw.text((70, 592), wrapped, fill=(255, 255, 255))
    img.save(out_img)


def generate_tv_cartoon(script_text, style_choice, progress=gr.Progress()):
    if not script_text.strip():
        return None, "⚠️ कृपया आधी ५ कॅरेक्टर्सची स्क्रिप्ट टाका!"

    os.makedirs("scenes", exist_ok=True)
    lines = [line.strip() for line in script_text.split("\n") if line.strip()]
    clips = []

    for i, line in enumerate(lines):
        progress((i + 1) / len(lines), desc=f"सीन {i+1}/{len(lines)} बनत आहे...")

        if ":" in line:
            parts = line.split(":", 1)
            char_raw = parts.strip().capitalize()
            dialogue = parts.strip()
            char_name = (
                char_raw if char_raw in CHARACTER_VOICES else "Narrator"
            )
        else:
            char_name = "Narrator"
            dialogue = line

        if len(dialogue) < 2:
            continue

        audio_file = f"scenes/voice_{i}.mp3"
        img_file = f"scenes/frame_{i}.jpg"

        asyncio.run(make_voice(dialogue, char_name, audio_file))
        make_cartoon_frame(dialogue, char_name, style_choice, i, img_file)

        audio_clip = AudioFileClip(audio_file)
        dur = audio_clip.duration + 0.3

        if i % 2 == 0:
            img_clip = (
                ImageClip(img_file)
                .set_duration(dur)
                .resize(lambda t: 1 + 0.05 * t)
            )
        else:
            img_clip = (
                ImageClip(img_file)
                .set_duration(dur)
                .resize(lambda t: 1.08 - 0.04 * t)
            )

        video_clip = img_clip.set_position(("center", "center")).set_audio(
            audio_clip
        )
        clips.append(video_clip)

    progress(0.95, desc="सर्व डायलॉग्स जोडून फायनल MP4 व्हिडिओ बनवत आहे...")
    final_video = concatenate_videoclips(clips, method="compose")
    output_mp4 = "My_TV_Cartoon_Episode.mp4"

    final_video.write_videofile(
        output_mp4, fps=24, codec="libx264", audio_codec="aac", threads=4
    )
    return (
        output_mp4,
        "✅ तुझा 5-Character TV Cartoon एपिसोड तयार आहे! खालील बटनावरून MP4 डाउनलोड कर.",
    )


sample_script = """Narrator: एक सुंदर गांव में राजू और रानी अपने दादा-दादी और राजा के साथ रहते थे।
Raju: अरे रानी देखो! जंगल के पास यह चमकता हुआ जादुई पत्थर किसका है?
Rani: संभलकर राजू! लगता है यह कोई जादुई खजाने का रास्ता है।
Dadi: बच्चों, जल्दी घर आ जाओ, अंधेरा होने वाला है!
Raja: शाबाश बच्चों! तुमने हमारे राज्य का खोया हुआ जादुई रत्न ढूंढ निकाला है।"""

with gr.Blocks(theme=gr.themes.Soft()) as studio:
    gr.Markdown("# 🎬 विशालचा स्वतःचा 5-Character TV Cartoon Studio")
    gr.Markdown(
        "**कॅरेक्टर्स वापरा:** `Raju:`, `Rani:`, `Raja:`, `Dadi:`, `Narrator:`"
    )

    with gr.Row():
        with gr.Column():
            script_box = gr.Textbox(
                lines=12,
                value=sample_script,
                label="तुझी ५ कॅरेक्टर्सची स्क्रिप्ट इथे टाक",
            )
            style_box = gr.Dropdown(
                choices=[
                    "3D Pixar Disney movie animation style, cute Indian cartoon characters, vibrant colors",
                    "2D Indian TV cartoon style like Chhota Bheem and Motu Patlu, bright colors",
                    "Anime Studio Ghibli magical cartoon style, detailed background",
                ],
                value="3D Pixar Disney movie animation style, cute Indian cartoon characters, vibrant colors",
                label="कार्टून स्टाईल निवड",
            )
            run_btn = gr.Button(
                "🚀 5-Character कार्टून MP4 व्हिडिओ बनवा", variant="primary"
            )

        with gr.Column():
            status_out = gr.Textbox(label="स्टेटस")
            video_out = gr.Video(label="तयार कार्टून व्हिडिओ (MP4)")

    run_btn.click(
        fn=generate_tv_cartoon,
        inputs=[script_box, style_box],
        outputs=[video_out, status_out],
    )

studio.launch(server_name="0.0.0.0", server_port=7860)
