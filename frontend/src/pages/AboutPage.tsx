import AlexPhoto from "../assets/Alex.jpg"
import TimPhoto from "../assets/Tim.jpg"
import EugenPhoto from "../assets/Eugen.jpg"
import NikitaPhoto from "../assets/Nikita.jpg"
import IvanPhoto from "../assets/Ivan.jpg"

import OP_logo from "../assets/OP_logo.svg"
import SPbguLogo from "../assets/spbgu_logo.svg"

import {RED} from "../config.ts"

const AboutPage = () => {
    const teamMembers = [
        {name: "Александр Александрович Ерхов", role: "Architect", photo: AlexPhoto},
        {name: "Тимофей Витальевич Скворчевский", role: "Frontend", photo: TimPhoto},
        {name: "Евгений Юрьевич Бычков", role: "Team Lead && Backend", photo: EugenPhoto},
        {name: "Никита Андреевич Насибуллин", role: "Backend", photo: NikitaPhoto},
        {name: "Иван Сергеевич Овсюков", role: "Тестировщик", photo: IvanPhoto},
    ]

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-8">

            {/* Title */}
            <h1
                className="text-3xl md:text-4xl font-extrabold mb-4 text-center"
                style={{color: RED}}
            >
                About Drone Analytics
            </h1>
            <p className="text-gray-700 text-center max-w-2xl mb-12">
                Этот сайт создан для аналитики логов с дронов. Он позволяет визуализировать события, телеметрию и
                команды,
                а также анализировать безопасность полетов. Наш инструмент помогает эффективно контролировать работу
                дронов и выявлять ошибки на ранних этапах.
            </p>

            {/* Command */}
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Наша команда</h2>
            <div className="flex flex-wrap justify-center gap-6 mb-12 p-[20px]">
                {teamMembers.map((member) => (
                    <div
                        key={member.name}
                        className="flex-shrink-0 w-56 flex flex-col items-center bg-white rounded-xl shadow-lg p-4"
                    >
                        <img
                            src={member.photo}
                            alt={member.name}
                            className="w-24 h-24 rounded-full object-cover mb-3"
                        />
                        <h3 className="font-semibold text-gray-800 text-center whitespace-pre-line leading-tight">
                            {member.name}
                        </h3>
                        <p className="text-gray-600 text-sm text-center">
                            {member.role}
                        </p>
                    </div>
                ))}
            </div>

            {/* Sponsors */}
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Наши посредники</h2>
            <div className="flex items-center gap-12">
                <div className="flex items-center gap-3">
                    <img src={OP_logo} alt="OutPaint Company" className="h-12"/>
                    <span className="font-semibold text-sm leading-none text-left">
                    <span style={{color: RED}}>OurPaint</span>
                                        <br/>
                        <span className="text-gray-700">Company</span>
                        </span>
                </div>
                <div className="flex flex-col items-center">
                    <img src={SPbguLogo} alt="SPbGU" className="h-25 mb-2"/>
                </div>
            </div>
        </div>
    )
}

export default AboutPage