import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'TestForge AI — Quality, backed by evidence.',icons:{icon:'/favicon.svg'},description:'An auditable agentic QA workspace. Retrieve requirements, approve tests, and make evidence-based release decisions.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
