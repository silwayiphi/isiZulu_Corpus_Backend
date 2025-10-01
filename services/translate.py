from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

class Translator:
    def __init__(self):
        model_name = "facebook/nllb-200-distilled-600M"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    def translate(self, text: str, src_lang="eng_Latn", tgt_lang="zul_Latn"):
        # Set source language
        self.tokenizer.src_lang = src_lang

        # Encode
        encoded = self.tokenizer(text, return_tensors="pt")

        # ✅ Fix: use convert_tokens_to_ids for target language BOS token
        forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt_lang)

        # Generate translation
        generated_tokens = self.model.generate(
            **encoded,
            forced_bos_token_id=forced_bos_token_id
        )
        return self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]


# ✅ Initialize once
nllb_translator = Translator()
