// frontend/components/Sources.jsx
'use client';

import { FaLink } from 'react-icons/fa';

export default function Sources({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="flex items-center gap-4 flex-wrap">
      <span className="text-xs text-[#8e8fa0] flex items-center gap-1">
        <FaLink className="text-[#10a37f]" />
        <span>Sources:</span>
      </span>
      <div className="flex flex-wrap gap-2">
        {sources.map((url, index) => (
          <a
            key={index}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-[#10a37f] hover:text-[#0e8f6f] hover:underline transition-colors truncate max-w-[200px]"
          >
            {index + 1}. {new URL(url).hostname.replace('www.', '')}
          </a>
        ))}
      </div>
    </div>
  );
}