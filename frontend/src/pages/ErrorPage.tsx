import { Link, useRouteError } from "react-router-dom"

export default function ErrorPage() {
    const error: any = useRouteError()

    return (
        <div className="flex h-screen items-center justify-center bg-gray-100">
            <div className="text-center">

                <h1 className="text-6xl font-bold text-red-500">404</h1>

                <h2 className="text-2xl mt-4 font-semibold">
                    Unexpected Application Error
                </h2>

                <p className="mt-2 text-gray-600">
                    {error?.statusText || error?.message || "Page not found"}
                </p>

                <Link
                    to="/"
                    className="inline-block mt-6 px-6 py-3 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                    Go Home
                </Link>

            </div>
        </div>
    )
}