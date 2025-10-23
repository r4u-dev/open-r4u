import { describe, it, expect } from 'vitest';

// Simple test for markdown conversion logic
describe('Markdown conversion', () => {
  const markdownToHtml = (markdown: string): string => {
    // Split into lines for better processing
    const lines = markdown.split('\n');
    const processedLines: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i];
      
      // Skip empty lines (will be handled as spacing)
      if (line.trim() === '') {
        processedLines.push('<br>');
        continue;
      }
      
      // Headers
      if (line.match(/^### /)) {
        line = line.replace(/^### (.*)/, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>');
      } else if (line.match(/^## /)) {
        line = line.replace(/^## (.*)/, '<h2 class="text-xl font-semibold mt-6 mb-3">$1</h2>');
      } else if (line.match(/^# /)) {
        line = line.replace(/^# (.*)/, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>');
      }
      // Lists
      else if (line.match(/^- \[ \] /)) {
        line = line.replace(/^- \[ \] (.*)/, '<div class="flex items-center gap-2 ml-4"><input type="checkbox" disabled class="rounded"> <span>$1</span></div>');
      } else if (line.match(/^- \[x\] /)) {
        line = line.replace(/^- \[x\] (.*)/, '<div class="flex items-center gap-2 ml-4"><input type="checkbox" checked disabled class="rounded"> <span>$1</span></div>');
      } else if (line.match(/^- /)) {
        line = line.replace(/^- (.*)/, '<div class="ml-4">• $1</div>');
      } else if (line.match(/^\* /)) {
        line = line.replace(/^\* (.*)/, '<div class="ml-4">• $1</div>');
      } else if (line.match(/^\d+\. /)) {
        line = line.replace(/^(\d+)\. (.*)/, '<div class="ml-4">$1. $2</div>');
      }
      // Regular paragraph
      else {
        line = `<p class="mb-2">${line}</p>`;
      }
      
      // Apply inline formatting
      line = line.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>');
      line = line.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');
      line = line.replace(/`([^`]+)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm">$1</code>');
      
      processedLines.push(line);
    }
    
    // Handle code blocks (multi-line)
    let html = processedLines.join('');
    html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-muted p-3 rounded-md overflow-x-auto my-4"><code>$1</code></pre>');
    
    return html;
  };

  it('converts headers correctly', () => {
    const markdown = '# Header 1\n## Header 2\n### Header 3';
    const html = markdownToHtml(markdown);
    
    expect(html).toContain('<h1 class="text-2xl font-bold mt-8 mb-4">Header 1</h1>');
    expect(html).toContain('<h2 class="text-xl font-semibold mt-6 mb-3">Header 2</h2>');
    expect(html).toContain('<h3 class="text-lg font-semibold mt-4 mb-2">Header 3</h3>');
  });

  it('converts lists correctly', () => {
    const markdown = '- Item 1\n* Item 2\n1. Numbered item';
    const html = markdownToHtml(markdown);
    
    expect(html).toContain('<div class="ml-4">• Item 1</div>');
    expect(html).toContain('<div class="ml-4">• Item 2</div>');
    expect(html).toContain('<div class="ml-4">1. Numbered item</div>');
  });

  it('converts checkboxes correctly', () => {
    const markdown = '- [ ] Unchecked\n- [x] Checked';
    const html = markdownToHtml(markdown);
    
    expect(html).toContain('<input type="checkbox" disabled class="rounded"> <span>Unchecked</span>');
    expect(html).toContain('<input type="checkbox" checked disabled class="rounded"> <span>Checked</span>');
  });

  it('converts inline formatting correctly', () => {
    const markdown = '**bold** and *italic* and `code`';
    const html = markdownToHtml(markdown);
    
    expect(html).toContain('<strong class="font-semibold">bold</strong>');
    expect(html).toContain('<em class="italic">italic</em>');
    expect(html).toContain('<code class="bg-muted px-1 py-0.5 rounded text-sm">code</code>');
  });

  it('handles empty lines correctly', () => {
    const markdown = 'Line 1\n\nLine 2';
    const html = markdownToHtml(markdown);
    
    expect(html).toContain('<br>');
  });
});