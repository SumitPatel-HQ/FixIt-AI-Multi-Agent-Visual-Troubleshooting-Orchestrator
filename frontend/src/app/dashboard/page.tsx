import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

export default function Dashboard() {
   return (
      <div className="min-h-screen bg-background p-8 flex flex-col items-center justify-center">
         <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none"></div>

         <Card className="w-full max-w-md relative z-10">
            <CardHeader>
               <CardTitle>Welcome to Dashboard</CardTitle>
               <CardDescription>This is a placeholder for the future dashboard.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
               <p className="text-muted-foreground">
                  You have successfully navigated from the landing page.
               </p>
               <Link href="/">
                  <Button variant="outline" className="w-full">
                     Back to Home
                  </Button>
               </Link>
            </CardContent>
         </Card>
      </div>
   );
}
