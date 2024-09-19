# klmbr

klmbr - a prompt pre-processing technique to induce retokenization of the input for the LLMs.

---

https://github.com/user-attachments/assets/5141c554-38aa-4615-a9e5-7be9fe53c81b

---

### Technique overview

Let's imagine that the LLM was trained on this sentence (and most likely, it was):

```text
The sky is blue
```

We can almost safely assume that these inputs were tokenized on a word-by-word basis:

![screenshot of the "The sky is blue" tokenization](./assets/sky-tokens.png)

