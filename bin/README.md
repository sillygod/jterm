# Web Terminal Media Viewing Commands

These commands allow you to view media files directly in the web terminal.

## Installation

Add the bin directory to your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$PATH:/Users/jing/Downloads/mycrafts/jterm/bin"

# Or create symlinks
sudo ln -s /Users/jing/Downloads/mycrafts/jterm/bin/imgcat /usr/local/bin/imgcat
sudo ln -s /Users/jing/Downloads/mycrafts/jterm/bin/vidcat /usr/local/bin/vidcat
sudo ln -s /Users/jing/Downloads/mycrafts/jterm/bin/mdcat /usr/local/bin/mdcat
```

## Commands

### imgcat - Display Images

View images inline in the terminal:

```bash
imgcat photo.jpg
imgcat screenshot.png
imgcat diagram.svg
```

**Supported formats:** jpg, jpeg, png, gif, webp, bmp, svg

### vidcat - Play Videos

Play videos in the terminal viewer:

```bash
vidcat demo.mp4
vidcat screencast.webm
vidcat tutorial.mov
```

**Supported formats:** mp4, webm, ogg, mov, avi
**Max size:** 50MB

### mdcat - View Markdown

Render markdown files with GitHub-flavored styling:

```bash
mdcat README.md
mdcat documentation.md
```

**Supported formats:** md, markdown

### htmlcat - Preview HTML

Preview HTML files in a sandboxed iframe:

```bash
htmlcat index.html
htmlcat page.htm
```

**Supported formats:** html, htm
**Security:** JavaScript disabled by default for safety

### jwtcat - Decode JWT Tokens

Decode and inspect JSON Web Tokens (JWT):

```bash
jwtcat <token>
jwtcat token.txt
jwtcat --clipboard
echo $JWT_TOKEN | jwtcat
```

**Features:**
- Decode JWT header and payload
- Display in JSON or Claims Table format
- Optional signature verification
- Copy functionality for all sections
- Support for HMAC and RSA algorithms

## How It Works

These commands send OSC (Operating System Command) escape sequences to the terminal, which are intercepted by the web terminal's JavaScript and trigger the media viewer.

The escape sequence format is:
```
\033]1337;ViewImage=/path/to/file\007
```

## Examples

```bash
# View a screenshot
imgcat ~/Desktop/screenshot.png

# Play a video recording
vidcat ~/Videos/demo.mp4

# Read documentation
mdcat ~/projects/myapp/README.md
```

## Troubleshooting

If the commands don't work:

1. Make sure you're using the web terminal (not a regular terminal)
2. Refresh the browser page
3. Check browser console for errors
4. Verify file paths are absolute (use `realpath` to check)
