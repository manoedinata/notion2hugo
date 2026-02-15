# notion2hugo

A custom Python exporter designed to bridge Notion and Hugo, allowing you to seamlessly use Notion as a powerful headless CMS for your static blog.

## Overview

`notion2hugo` automates the process of fetching content from a Notion database and converting it into Hugo-compatible markdown. Instead of manually exporting files, this script handles content formatting, asset downloading, and directory structuring, making it perfect for automated CI/CD publishing pipelines.

## Features

- **Notion as a Headless CMS**: Write, edit, and manage your blog posts entirely within Notion.
- **Hugo Leaf Bundle Support**: Automatically converts Notion pages into Hugo's Leaf Bundle format. Content is neatly organized into `/content/posts/<slug>/index.md`, keeping markdown and its associated assets together.
- **Automated Image Handling**: Detects and downloads images embedded in your Notion pages directly to the respective Leaf Bundle directory, ensuring your assets are self-hosted and load reliably.
- **CLI Configuration**: Easily specify the target output directory and other parameters via command-line arguments.
- **CI/CD Ready**: Built specifically to integrate with GitHub Actions. It can be scheduled to run automatically, keeping your blog continuously in sync with your Notion database.

## How it Works

1. **Draft in Notion**: Create your content in a designated Notion database.
2. **Fetch & Convert**: The Python script connects to the Notion API, pulls the latest pages, and transforms the Notion blocks into Markdown with Hugo-compatible frontmatter.
3. **Download Assets**: Any images within the Notion page are downloaded locally.
4. **Generate Bundles**: The script outputs the final `index.md` and images into the specified output directory.

## Usage

To run the script locally, ensure you have your Notion API credentials configured, then run the exporter using the CLI arguments to define your output path:

```bash
# Example command to run the exporter
python main.py --output /path/to/hugo/content/posts
