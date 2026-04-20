from pathlib import Path

from anki_builder.schema import Card

_pipe = None


def _get_pipeline():
    global _pipe
    if _pipe is None:
        from diffusers import AutoPipelineForText2Image
        import torch

        _pipe = AutoPipelineForText2Image.from_pretrained(
            "stabilityai/sdxl-turbo",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            variant="fp16" if torch.cuda.is_available() else None,
        )
        device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
        _pipe = _pipe.to(device)
    return _pipe


def _build_image_prompt(word: str) -> str:
    return (
        f"Simple, colorful illustration of '{word}' suitable for children aged 9-12. "
        f"Friendly cartoon style, no text in the image, white background."
    )


def generate_image_for_card(card: Card, media_dir: Path) -> Card:
    image_path = media_dir / f"{card.id}_image.png"

    if card.image_file and Path(card.image_file).exists():
        return card

    if image_path.exists():
        return card.model_copy(update={"image_file": str(image_path)})

    pipe = _get_pipeline()
    prompt = _build_image_prompt(card.word)
    image = pipe(
        prompt=prompt,
        num_inference_steps=4,
        guidance_scale=0.0,
        width=512,
        height=512,
    ).images[0]

    image.save(str(image_path))
    return card.model_copy(update={"image_file": str(image_path)})


def generate_image_batch(cards: list[Card], media_dir: Path) -> list[Card]:
    return [generate_image_for_card(card, media_dir) for card in cards]
