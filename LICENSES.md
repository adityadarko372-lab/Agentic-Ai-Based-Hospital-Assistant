# Third-party data and models (optional Phase 5 features)

The required Nova Health demo uses only the project's own code and fictional
data. The optional features below download third-party material at setup time.
None of it is committed to this repository.

| Item | Where it is used | Licence | Source |
|---|---|---|---|
| MedQuAD | Health Information Agent passages (shown with source and licence) | CC BY 4.0 | https://github.com/abachaa/MedQuAD |
| CLINC150 | Training examples for the intent classifier | CC BY 3.0 | https://github.com/clinc/oos-eval |
| all-MiniLM-L6-v2 | Sentence encoder for MedQuAD search | Apache 2.0 | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 |
| distilbert-base-uncased | Base model for the intent classifier | Apache 2.0 | https://huggingface.co/distilbert/distilbert-base-uncased |
| Qwen2.5 3B (via Ollama) | Optional rewording of some replies | Qwen Research License (research or evaluation use only) | https://ollama.com/library/qwen2.5:3b-instruct/blobs/b5c0e5cf74cf |
| Ollama | Local model runtime | MIT | https://github.com/ollama/ollama |

MedQuAD answers come from U.S. NIH websites. Nova Health shows them as general
educational information, labelled as such, with a link to the original page.
They are not medical advice and may not match practice in India.

The Qwen2.5 3B licence allows use "for research or evaluation purposes only",
which covers this academic prototype. Any commercial use would need a licence
from Alibaba Cloud or a different model (OLLAMA_MODEL can point to another one).
"Qwen is licensed under the Qwen RESEARCH LICENSE AGREEMENT, Copyright (c)
Alibaba Cloud. All Rights Reserved."
