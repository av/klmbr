import random

mods = [
    "capitalize",
    "diacritic",
    'leetspeak',
    "remove_vowel",
]

def randomize(text, percentage):
    if not text:
        return "", {} # Return empty string and empty mapping if input is empty

    if not 0 <= percentage <= 100:
        raise ValueError("Percentage must be between 0 and 100")

    words = text.split()
    chars = list(text)
    num_chars_to_modify = max(1, int(len(chars) * (percentage / 100)))
    indices_to_modify = random.sample(range(len(chars)), num_chars_to_modify)
    word_mapping = {}

    for idx in indices_to_modify:
        modification = random.choice(mods)

        # Find the word that contains the current character
        current_length = 0
        for word_idx, word in enumerate(words):
            if current_length <= idx < current_length + len(word):
                original_word = word
                word_start_idx = current_length
                break
            current_length += len(word) + 1 # +1 for the space
        else:
            # If we're here, we're likely dealing with a space or the last character
            continue

        if modification == "capitalize":
            chars[idx] = chars[idx].swapcase()
        elif modification == "diacritic":
            if chars[idx].isalpha():
                diacritics = ["̀", "́", "̂", "̃", "̈", "̄", "̆", "̇", "̊", "̋"]
                chars[idx] = chars[idx] + random.choice(diacritics)
        elif modification == "leetspeak":
            leetspeak_map = {
                "a": "4", "e": "3", "i": "1", "o": "0", "s": "5",
                "t": "7", "b": "8", "g": "9", "l": "1",
            }
            chars[idx] = leetspeak_map.get(chars[idx].lower(), chars[idx])
        elif modification == "remove_vowel":
            if chars[idx].lower() in "aeiou":
                chars[idx] = ""

        modified_word = "".join(
            chars[word_start_idx : word_start_idx + len(original_word)]
        )

        if modified_word != original_word:
            # Clean up both the modified word and the original word
            cleaned_modified_word = modified_word.rstrip('.,')
            cleaned_original_word = original_word.rstrip('.,')
            word_mapping[cleaned_modified_word] = cleaned_original_word

    modified_text = "".join(chars)
    return modified_text, word_mapping
