export default function Sources({ results }) {

    if (!results) return null;

    return (

        <div className="mt-8">

            <h2 className="font-bold mb-3">
                📚 Sources
            </h2>

            <div className="space-y-2">

                {results.map((r, i) => (

                    <a

                        key={i}

                        href={r.url}

                        target="_blank"

                        className="block text-blue-400 hover:underline"

                    >

                        {i + 1}. {r.title}

                    </a>

                ))}

            </div>

        </div>

    );

}