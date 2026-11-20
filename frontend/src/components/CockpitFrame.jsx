import React from 'react';

export default function CockpitFrame() {
  return (
    <>
      {/* Космический фон */}
      <div className="absolute inset-0 z-[-10] overflow-hidden bg-[#02060c]">
        <div className="nebula"></div>
        <div className="sun"></div>
        <div className="earth"></div>
        <div className="moon"></div>
        <div className="glass"></div>
      </div>

      {/* Объёмная рама кабины (SVG) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none z-40 drop-shadow-[0_8px_12px_#000]" viewBox="0 0 1600 900" preserveAspectRatio="none">
        <defs>
          <linearGradient id="metal" x2=".2" y2="1">
            <stop stopColor="#526875" />
            <stop offset=".25" stopColor="#172631" />
            <stop offset=".6" stopColor="#0a121b" />
            <stop offset="1" stopColor="#354a57" />
          </linearGradient>
          <linearGradient id="pillar">
            <stop stopColor="#03080e" />
            <stop offset=".4" stopColor="#304654" />
            <stop offset=".52" stopColor="#526976" />
            <stop offset=".65" stopColor="#192a37" />
            <stop offset="1" stopColor="#050b12" />
          </linearGradient>
        </defs>
        <path d="M0 0H1600V130L1470 116 1355 91H245L130 116 0 130Z" fill="url(#metal)" stroke="#607785" strokeWidth="2"/>
        <path d="M0 115L130 133 280 657 224 700 0 340Z" fill="url(#pillar)" stroke="#4b6372" strokeWidth="2"/>
        <path d="M1600 115L1470 133 1320 657 1376 700 1600 340Z" fill="url(#pillar)" stroke="#4b6372" strokeWidth="2"/>
        <path d="M0 105L116 123 265 653M1600 105L1484 123 1335 653" fill="none" stroke="#67c9df" strokeOpacity=".65" strokeWidth="3"/>
        <path d="M245 90H1355" fill="none" stroke="#88e9ff" strokeOpacity=".5" strokeWidth="3"/>
        <path d="M0 635L220 650 390 692H1210L1380 650 1600 635V710H0Z" fill="url(#metal)" stroke="#6f8690" strokeWidth="2"/>
        <g fill="#ffae56">
          <rect x="200" y="73" width="30" height="3"/>
          <rect x="1370" y="73" width="30" height="3"/>
        </g>
      </svg>
    </>
  );
}
