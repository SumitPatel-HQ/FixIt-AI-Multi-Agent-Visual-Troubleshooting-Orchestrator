import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
   try {
      // Parse the form data
      const formData = await request.formData();

      const image = formData.get('image') as File;
      const query = formData.get('query') as string;
      const deviceHintStr = formData.get('device_hint') as string;

      // Validate required fields
      if (!image) {
         return NextResponse.json(
            { error: 'Image is required' },
            { status: 400 }
         );
      }

      if (!query) {
         return NextResponse.json(
            { error: 'Query is required' },
            { status: 400 }
         );
      }

      // Parse device hint if provided
      let deviceHint = null;
      if (deviceHintStr) {
         try {
            deviceHint = JSON.parse(deviceHintStr);
         } catch (e) {
            console.error('Failed to parse device hint:', e);
         }
      }

      // Log the received data (for debugging)
      console.log('Received troubleshooting request:', {
         imageSize: image.size,
         imageType: image.type,
         query,
         deviceHint,
      });

      // TODO: Replace this with actual backend API call
      // For now, simulate processing and return a mock session ID
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate processing delay

      const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      return NextResponse.json({
         success: true,
         sessionId,
         message: 'Troubleshooting request received successfully',
      });

   } catch (error) {
      console.error('Error processing troubleshooting request:', error);
      return NextResponse.json(
         { error: 'Internal server error' },
         { status: 500 }
      );
   }
}

// Handle OPTIONS request for CORS
export async function OPTIONS() {
   return new NextResponse(null, {
      status: 200,
      headers: {
         'Access-Control-Allow-Origin': '*',
         'Access-Control-Allow-Methods': 'POST, OPTIONS',
         'Access-Control-Allow-Headers': 'Content-Type',
      },
   });
}
