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
    - I used Stable Diffusion 3.5 in [Google Colab](https://colab.research.google.com/drive/18-cI6RDPRQ6yiflSWAe1QSfFK6A8-i1_?usp=sharing).
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
- The Adventures of Tom Sawyer – Mark Twain (102,181 tokens)
- Peter Pan – J. M. Barrie (65,530 tokens)
- The Idiot – Fyodor Dostoyevsky (339,041 tokens)
- Anna Karenina – Leo Tolstoy (486,537 tokens)
- Les Misérables – Victor Hugo (783,912 tokens)
For all of them I downloaded txt files from [Project Guttenberg](https://www.gutenberg.org/).

## Some Observations
- Smaller books process surprisingly well
- Iterative approach (JSON from previous iteration is given as draft within prompt) helps refine results
- 8K output is the main bottleneck, so even without description and prompt, final JSON does not fit for books with large numbers of characters like Les Misérables
- Multiple copies of a book in prompt (-cp option) don't help a lot; in some cases, they even make results worse


## Things to Try
- Test other large context window models
- Define 'ground truth' character networks using more sophisticated analysis and use it as benchmark for huge context models
- Try it on legal documents (affidavits, indictments, depositions), historical documents and movie/TV show scripts

## Disclaimer
This is not an attempt to determine the best method for extracting characters and relationships from books. A more effective approach would likely involve processing the text in segments and extracting different types of information in separate steps. The goal here is simply to explore the limits of LLMs when given an entire book in a single prompt.
