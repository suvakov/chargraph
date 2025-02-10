# Character Graph Extraction from Books using LLMs

## Overview
Let's try a small experiment with LLMs: feed an entire book into the context window and ask it to generate a list of characters, their relationships, and physical descriptions—data that can later be used for image generation.

## TL;DR
Jump directly to [visualisation](https://suvakov.github.io/chargraph/) to explore character networks from few books extracted using Gemini 2.0 Flash Exp:


[![visualisation](snapshot.png)](https://suvakov.github.io/chargraph/)

## Process
1. Script chargraph.py is used to extract characters and relationships.
    - Check [documentation](chargraph.md) how to run it
    - It supports Gemini and OpenRouter API
2. (Optional) Character images were generated using portrait_prompt from JSON.
    - I used Stable Diffusion 3.5 in [Google Colab](https://colab.research.google.com/drive/18-cI6RDPRQ6yiflSWAe1QSfFK6A8-i1_?usp=sharing) for Peter Pan and Tom Sawyer.
    - Note: Prompts exclude character/book names to avoid bias from pre-trained character appearances. You can see prompt in visualization by clicking on character.

3. Results are visualized in HTML/JS using D3.
    - Check [documentation](visualization.md) how to add your books in visualisation 📖

## Model Used
- **Model**: Gemini 2.0 Flash Exp
- **Specs**: 1M token context window, 8K token output limit
- **Why this one?**: 
    - Supports function calls / structured output
    - Large context window (can fit Les Misérables)
    - Free of charge (you can get API key from [AI Studio](https://aistudio.google.com))

## Books Processed

| Book Title | Author | Tokens |
|-----------|-------|-------|
| The Adventures of Tom Sawyer | Mark Twain | 102,181 |
| Peter Pan | J. M. Barrie | 65,530 |
| The Idiot | Fyodor Dostoyevsky | 339,041 |
| Anna Karenina | Leo Tolstoy | 486,537 |
| Les Misérables | Victor Hugo | 783,912 |

All text files were downloaded from [Project Gutenberg](https://www.gutenberg.org/).

## Some Observations
- Small books (Tom Sawyer and Peter Pan) are processed surprisingly well, with relatively accurate character identification and relationship mapping
- Iterative approach (using JSON from previous iteration as draft within prompt) helps refine results and adds some missing links and characters
- 8K token output limit is the main bottleneck, making it challenging to process books with large character counts like Les Misérables, even without physical description (-portrait option) and limited character description to 2 sentences (-desc 2). In those cases, after few iterations, LLM will fail to finish JSON reaching max output. However, after few runs without (-portrait), it is possible to get some result, with relatively good description of character roles but with a lot of links missing.
- Multiple copies of a book, when possible to fit in the prompt (-cp option), don't help a lot; in some cases with a large number of copies (5-10), they even make results worse

## Things to Try
- Improve prompt
- Test other large context window models
- Find 'ground truth' character networks using more sophisticated analysis and use it as benchmark for large context models
- Try it on legal documents (affidavits, indictments), historical documents and movie/TV show scripts

## Disclaimer
This is not an attempt to determine the best method for extracting characters and relationships from books. A more effective approach would likely involve processing the text in segments and extracting different types of information in separate steps. The goal here is simply to explore the limits of LLMs when given an entire book in a single prompt.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=suvakov/chargraph&type=Date)](https://star-history.com/#suvakov/chargraph&Date)
