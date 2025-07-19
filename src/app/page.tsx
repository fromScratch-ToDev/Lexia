'use client'

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { CheckCircle, FileText, Sparkles } from "lucide-react"
import { motion } from "framer-motion"
import Link from "next/link"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-gray-900 px-6 py-12 md:px-16">
      <motion.div 
        initial={{ opacity: 0, y: -40 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ duration: 0.8 }}
        className="max-w-5xl mx-auto text-center"
      >
        <h1 className="text-4xl md:text-6xl font-bold mb-6">
          Assistant IA Juridique<br className="hidden md:block" />
          <span className="text-blue-600">local et confidentiel</span>
        </h1>
        <p className="text-lg md:text-xl mb-8">
          Gagnez du temps, sécurisez vos documents, restez maître de vos données. 
          Analysez et résumez vos PDF juridiques avec une IA spécialisée, sans quitter votre machine.
        </p>
        <div className="flex justify-center gap-4">
          <Link href={"/ai-tools"}>
            <Button className="cursor-pointer text-lg px-6 py-4">Essayer la démo</Button>
          </Link>
          <Button variant="outline" className="text-lg px-6 py-4">En savoir plus</Button>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-6xl mx-auto">
        <Card className="rounded-2xl shadow-md">
          <CardContent className="p-6">
            <FileText className="w-8 h-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Analyse de documents</h3>
            <p>Importez vos contrats, jugements ou courriers. L'IA extrait et résume automatiquement les points clés.</p>
          </CardContent>
        </Card>

        <Card className="rounded-2xl shadow-md">
          <CardContent className="p-6">
            <Sparkles className="w-8 h-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Confidentialité totale</h3>
            <p>Tout fonctionne en local : aucune donnée n'est envoyée en ligne. Conforme au RGPD et au secret professionnel.</p>
          </CardContent>
        </Card>

        <Card className="rounded-2xl shadow-md">
          <CardContent className="p-6">
            <CheckCircle className="w-8 h-8 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Simplicité d'usage</h3>
            <p>Glissez-déposez vos fichiers. Posez des questions. Obtenez des réponses en quelques secondes.</p>
          </CardContent>
        </Card>
      </div>

      <div className="mt-24 text-center max-w-2xl mx-auto">
        <h2 className="text-3xl font-bold mb-4">Restez informé du lancement</h2>
        <p className="text-gray-600 mb-6">Recevez une notification dès que l’outil est disponible.</p>
        <div className="flex justify-center gap-2">
          <Input placeholder="Votre adresse e-mail" className="max-w-xs" />
          <Button>S'inscrire</Button>
        </div>
      </div>
    </div>
  )
}
