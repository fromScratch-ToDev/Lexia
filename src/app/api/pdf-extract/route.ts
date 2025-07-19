import { NextRequest, NextResponse } from 'next/server';
import pdfParse from 'pdf-parse';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('pdf') as File;

    if (!file) {
      return NextResponse.json({ error: 'No PDF file uploaded' }, { status: 400 });
    }

    const buffer = await file.arrayBuffer();
    
    try {
      // Première tentative avec pdf-parse
      const data = await pdfParse(Buffer.from(buffer));
      
      return NextResponse.json({ 
        text: data.text,
        filename: file.name,
        pages: data.numpages || 1
      });
    } catch (parseError: any) {
      console.warn('PDF parse error, retrying with different options:', parseError.message);
      
      // Deuxième tentative avec options plus permissives
      try {
        const data = await pdfParse(Buffer.from(buffer), {
          // Options pour gérer les PDFs problématiques
          max: 0, // Pas de limite de pages
          version: 'v1.10.100'
        });
        
        return NextResponse.json({ 
          text: data.text,
          filename: file.name,
          pages: data.numpages || 1
        });
      } catch (secondError: any) {
        console.error('Second PDF parse attempt failed:', secondError.message);
        
        // Troisième tentative : extraire ce qu'on peut
        try {
          // Tentative de lecture partielle
          const data = await pdfParse(Buffer.from(buffer), {
            max: 1, // Juste la première page pour tester
          });
          
          // Si ça marche pour une page, essayer toutes les pages
          const fullData = await pdfParse(Buffer.from(buffer), {
            max: 0,
          });
          
          return NextResponse.json({ 
            text: fullData.text || "Contenu partiellement extrait",
            filename: file.name,
            pages: fullData.numpages || 1
          });
        } catch (finalError: any) {
          console.error('All PDF parse attempts failed:', finalError.message);
          
          // Retourner une erreur plus informative
          return NextResponse.json({ 
            error: 'PDF parsing failed',
            details: `Impossible d'extraire le texte de ce PDF. Erreur: ${finalError.message}`,
            filename: file.name
          }, { status: 422 });
        }
      }
    }
  } catch (error: any) {
    console.error('General PDF processing error:', error);
    return NextResponse.json({ 
      error: 'Failed to process PDF',
      details: error.message 
    }, { status: 500 });
  }
}
