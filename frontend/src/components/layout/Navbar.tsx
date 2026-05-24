"use client"

import * as React from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Menu, X } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { SignInButton, SignUpButton, UserButton, Show, useUser } from "@clerk/nextjs"
import { useRouter } from "next/navigation"

function NavbarActions({ setIsOpen }: { setIsOpen: (open: boolean) => void }) {
   const { isSignedIn } = useUser()
   const router = useRouter()

   if (isSignedIn) {
      return (
         <>
            <Button
               size="sm"
               className="hidden xs:flex rounded-full px-5 h-9 text-xs font-bold tracking-wide shadow-lg shadow-white/5 active:scale-95 transition-transform"
               onClick={() => router.push("/dashboard")}
            >
               Dashboard
            </Button>
            <div className="hidden md:flex items-center pl-1">
               <UserButton afterSignOutUrl="/" />
            </div>
         </>
      )
   }

   return (
      <>
         <Link href="/dashboard" className="hidden xs:block">
            <Button size="sm" className="rounded-full px-5 h-9 text-xs font-bold tracking-wide shadow-lg shadow-white/5 active:scale-95 transition-transform">
               Get Started
            </Button>
         </Link>
         <Show when="signed-out">
            <SignUpButton mode="modal" fallbackRedirectUrl="/">
               <Button variant="ghost" size="sm" className="hidden md:inline-flex rounded-full text-md font-semibold hover:bg-white/5 cursor-pointer">
                  Sign Up
               </Button>
            </SignUpButton>
            <SignInButton mode="modal" fallbackRedirectUrl="/">
               <Button variant="ghost" size="sm" className="hidden md:inline-flex rounded-full text-md font-semibold hover:bg-white/5 cursor-pointer">
                  LogIn
               </Button>
            </SignInButton>
         </Show>
      </>
   )
}

function MobileGetStarted({ setIsOpen }: { setIsOpen: (open: boolean) => void }) {
   const { isSignedIn } = useUser()
   const router = useRouter()

   if (isSignedIn) {
      return (
         <Button
            className="w-full rounded-xl py-6 text-base font-bold"
            onClick={() => { router.push("/dashboard"); setIsOpen(false) }}
         >
            Dashboard
         </Button>
      )
   }

   return (
      <Link href="/dashboard" onClick={() => setIsOpen(false)}>
         <Button className="w-full rounded-xl py-6 text-base font-bold">
            Get Started
         </Button>
      </Link>
   )
}

function MobileSignIn() {
   const { isSignedIn } = useUser()

   if (isSignedIn) {
      return (
         <div className="flex justify-center py-2">
            <UserButton afterSignOutUrl="/" />
         </div>
      )
   }

   return (
      <Show when="signed-out">
         <div className="flex flex-col gap-3">
            <SignUpButton mode="modal" fallbackRedirectUrl="/">
               <Button variant="secondary" className="w-full rounded-xl py-6 text-base font-bold">
                  Sign Up
               </Button>
            </SignUpButton>
            <SignInButton mode="modal" fallbackRedirectUrl="/">
               <Button variant="ghost" className="w-full rounded-xl py-6 text-base font-bold border border-white/10">
                  Sign In
               </Button>
            </SignInButton>
         </div>
      </Show>
   )
}

export function Navbar() {
   const [isOpen, setIsOpen] = React.useState(false)

   return (
      <>
         <motion.nav
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="fixed top-6 left-1/2 -translate-x-1/2 z-50 w-[calc(100%-2rem)] md:w-[calc(100%-3rem)] max-w-6xl"
         >
            <div className="flex md:grid md:grid-cols-3 items-center justify-between px-4 md:px-6 h-14 bg-background/40 backdrop-blur-xl border border-white/5 rounded-full shadow-[0_8px_32px_rgba(0,0,0,0.3)]">
               {/* Left: Logo */}
               <div className="flex justify-start px-5">
                  <Link href="/" className="flex items-center gap-2 group transition-transform hover:scale-105">
                     <span className="text-xl font-bold tracking-tight">Fixit</span>
                  </Link>
               </div>

               {/* Center: Links (Desktop) */}
               <div className="hidden md:flex items-center justify-center gap-8">
                  {["Features", "Pricing", "About"].map((item) => (
                     <Link
                        key={item}
                        href={`#${item.toLowerCase()}`}
                        className="text-md font-medium text-muted-foreground hover:text-foreground transition-all hover:scale-105"
                     >
                        {item}
                     </Link>
                  ))}
               </div>

               {/* Right: Actions */}
               <div className="flex items-center justify-end gap-2">
                  <NavbarActions setIsOpen={setIsOpen} />
                  <Button
                     variant="ghost"
                     size="icon"
                     className="md:hidden rounded-full hover:bg-white/10"
                     onClick={() => setIsOpen(!isOpen)}
                  >
                     {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                  </Button>
               </div>
            </div>
         </motion.nav>

         {/* Mobile Menu Overlay */}
         <AnimatePresence>
            {isOpen && (
               <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="fixed inset-x-4 top-24 z-50 md:hidden"
               >
                  <div className="bg-background/80 backdrop-blur-2xl border border-white/10 rounded-2xl p-6 shadow-2xl flex flex-col gap-4">
                     {["Features", "Pricing", "About"].map((item) => (
                        <Link
                           key={item}
                           href={`#${item.toLowerCase()}`}
                           onClick={() => setIsOpen(false)}
                           className="text-lg font-medium text-muted-foreground hover:text-foreground transition-colors py-2 border-b border-white/5"
                        >
                           {item}
                        </Link>
                     ))}
                     <div className="flex flex-col gap-3 pt-4">
                        <MobileGetStarted setIsOpen={setIsOpen} />
                        <MobileSignIn />
                     </div>
                  </div>
               </motion.div>
            )}
         </AnimatePresence>
      </>
   )
}
