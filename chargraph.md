# CharGraph - Character Relationship Analyzer

A Python script that analyzes text to extract characters, their relationships, and generates interactive network visualizations using Gemini API and NetworkX.

## Features

- 📖 Automatic character extraction from any text
- 🤝 Relationship mapping with weights and emotional valence
- 📊 Network visualization with matplotlib
- 🔄 Iterative refinement process
- 🖼️ AI portrait prompt generation (optional)
- 🤖 Multiple AI providers (Google Gemini and OpenRouter API)
- 🛠️ Configurable analysis parameters

## Requirements

- Python 3.10+
- Google Gemini API key ([AI Studio](https://aistudio.google.com)) or [OpenRouter](https://openrouter.ai/) API key
- NetworkX 3.0+
- matplotlib 3.7+
- google-generativeai 0.3.0+

## Installation
Clone repository, enter folder and run:
```bash
pip install -r requirements.txt
```
Set API key as environment variable:
```bash
export GEMINI_API_KEY="your-api-key-here"
```
or
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

## Usage

```bash
python chargraph.py [INPUT_FILE] [OUTPUT_BASE_NAME] [OPTIONS]

# Examples

python chargraph.py input.txt output.json \
  -iter 10 \
  -delay 10 \
  -plot \
  -desc 2 \
  -portrait \
  -cp 2 \
  -t 0.5

python chargraph.py input.txt output.json \
  -iter 10 \
  -delay 10 \
  -t 0.5 
  -or
  -m https://openrouter.ai/api/v1/chat/completions
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-iter N` | Number of analysis iterations (default: 1) |
| `-delay SECONDS` | Delay between iterations (default: 300) |
| `-prev FILE` | Previous JSON file for iterative refinement |
| `-plot` | Generate relationship network PNG |
| `-desc N` | Include N-sentence character descriptions |
| `-portrait` | Generate AI portrait prompts |
| `-cp N` | Number of text copies for analysis (default 1) |
| `-t FLOAT` | Creativity temperature (default 1.0) |
| `-or` | Use OpenRouter API |
| `-m MODEL` | Specify model (default: gemini-2.0-flash-exp:free) |

## Output Structure

```
data/
├── [output_base]_0.json      # First iteration results
├── [output_base]_0.png       # Relationship graph
├── [output_base]_0.debug.txt # Debug info
└── ...                       # Subsequent iterations
```

## Example Output

[Peter Pan](https://github.com/suvakov/chargraph/blob/main/data/peter_pan_9.json)

