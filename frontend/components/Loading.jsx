// frontend/components/Loading.jsx
'use client';

export default function Loading() {
  return (
    <div className="flex items-center gap-3 px-4 py-5 bg-[#444654]">
      <div className="w-8 h-8 rounded-full bg-[#10a37f] flex items-center justify-center">
        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
      </div>
      <div className="flex items-center gap-1">
        <span className="text-sm text-[#acacbe]">Generating report</span>
        <span className="animate-pulse text-[#acacbe]">...</span>
      </div>
    </div>
  );
}