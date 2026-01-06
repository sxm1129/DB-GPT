import React from 'react';

export default function ColorfulXSmartKG({ size = '1em', ...props }: { size?: string | number } & React.SVGProps<SVGSVGElement>) {
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 1024 1024" 
      fill="none" 
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <defs>
        <linearGradient id="xk-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1e88e5" />
          <stop offset="100%" stopColor="#26c6da" />
        </linearGradient>
      </defs>
      {/* 核心节点 */}
      <circle cx="512" cy="512" r="80" fill="url(#xk-gradient)" fillOpacity="0.8" />
      
      {/* X 形状的路径 & 节点 */}
      <path 
        d="M200 200 L450 450 M574 574 L824 824 M824 200 L574 450 M450 574 L200 824" 
        stroke="url(#xk-gradient)" 
        strokeWidth="48" 
        strokeLinecap="round" 
      />
      
      <circle cx="200" cy="200" r="40" fill="#1e88e5" />
      <circle cx="824" cy="824" r="40" fill="#26c6da" />
      <circle cx="824" cy="200" r="40" fill="#1e88e5" />
      <circle cx="200" cy="824" r="40" fill="#26c6da" />
      
      {/* 中间连接线条 */}
      <path 
        d="M512 432 L512 250 M512 592 L512 774 M432 512 L250 512 M592 512 L774 512" 
        stroke="url(#xk-gradient)" 
        strokeWidth="24" 
        strokeDasharray="40 20"
      />
    </svg>
  );
}
