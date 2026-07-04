export default function ChatInput({
    topic,
    setTopic,
    onSend
}) {

    return (

        <div className="border-t border-gray-700 p-4 flex gap-3">

            <input

                className="flex-1 rounded-xl bg-[#40414f] p-3 text-white"

                value={topic}

                onChange={(e) => setTopic(e.target.value)}

                placeholder="Ask anything..."

                onKeyDown={(e) => {
                    if (e.key === "Enter") onSend();
                }}

            />

            <button

                onClick={onSend}

                className="bg-green-600 px-5 rounded-xl"

            >

                Send

            </button>

        </div>

    );

}