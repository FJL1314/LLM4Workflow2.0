

import 'highlight.js/styles/atom-one-light.css';
import './markdown-styles.css';

import { useEffect, useState } from 'react';

import Markdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

const ReadmeViewer = () => {
  const [markdown, setMarkdown] = useState('');

  useEffect(() => {
    fetch('/README.md')
      .then((response) => response.text())
      .then((text) => {
        setMarkdown(text);
      })
      .catch((error) => console.error('Error fetching the README.md:', error));
  }, []);

  const components = {
    h1: ({ node, ...props }) => <h1 className="custom-h1" {...props} />,
    h2: ({ node, ...props }) => <h2 className="custom-h2" {...props} />,
    p: ({ node, ...props }) => <p className="custom-paragraph" {...props} />,
    code: ({ node, ...props }) => <code className="custom-code" {...props} />,
    li: ({ node, ...props }) => <li className="custom-list-item" {...props} />,
    ul: ({ node, ...props }) => <ul className="custom-list" {...props} />,
    ol: ({ node, ...props }) => (
      <ol className="custom-ordered-list" {...props} />
    ),
  };

  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      children={markdown}
      components={components}
    />
  );
};

export default ReadmeViewer;
