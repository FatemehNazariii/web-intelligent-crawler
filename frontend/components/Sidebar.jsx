export default function Sidebar() {
  return (
    <div className="w-64 bg-[#202123] text-white h-screen p-4">
      <button className="w-full border border-gray-600 rounded-lg p-3 hover:bg-gray-700">
        + New Chat
      </button>

      <div className="mt-8 text-gray-400 text-sm">
        <p className="mb-2">History</p>

        <div className="space-y-2">
          <div className="cursor-pointer hover:text-white">
            Artificial Intelligence
          </div>

          <div className="cursor-pointer hover:text-white">
            Climate Change
          </div>

          <div className="cursor-pointer hover:text-white">
            Cars
          </div>
        </div>
      </div>
    </div>
  );
}