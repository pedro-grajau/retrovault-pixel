import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title: 'RetroVault · Sua próxima aventura', description: 'Uma locadora retrô fictícia com Pixel, seu assistente de jogos.'};
export default function Layout({children}: {children: React.ReactNode}) {return <html lang="pt-BR"><body>{children}</body></html>;}
