export default function ChatMessage({ role, children }) {

    const isUser = role === "user";

    return (

        <div
            className={`flex ${isUser ? "justify-end" : "justify-start"} mb-6`}
        >

            <div
                className={`rounded-2xl p-4 max-w-3xl whitespace-pre-wrap
                ${isUser
                    ? "bg-blue-600 text-white"
                    : "bg-[#444654] text-white"
                }`}
            >

                {children}

            </div>

        </div>

    );

}