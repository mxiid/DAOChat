"use client"

import * as React from "react"
import { motion } from "framer-motion"

export default function AnimatedLogo({ thinking = false, isDarkMode = false }: { thinking?: boolean, isDarkMode?: boolean }) {
  const strokeColor = isDarkMode ? "white" : "black"

  return (
    <div className="flex items-center justify-center w-full h-full bg-transparent">
      <motion.svg
        viewBox="0 0 121.82 127.44"
        initial="hidden"
        animate={thinking ? "thinking" : "visible"}
        className={`w-full h-full ${thinking ? "animate-pulse" : ""}`}
        aria-label="Animated logo"
      >
        <motion.path
          d="M40.85,127.44c-12.58-7.27-25.14-14.58-37.78-21.76C.92,104.45,0,103.1,0,100.53Q.2,80,0,59.54a5.2,5.2,0,0,1,3-5.23C14.2,47.87,25.31,41.23,36.54,34.77c1.75-1,2.85-2.07,2.41-4.15-1.14-5.39,1.54-8.15,6.1-10.65C56,14,66.59,7.49,77.26,1.06a5.63,5.63,0,0,1,6.57,0Q101.31,11.43,119,21.47a4.94,4.94,0,0,1,2.83,5c-.11,13.66-.13,27.33,0,41,0,2.7-.94,4.09-3.18,5.39-11,6.39-21.94,13-33,19.39a4.24,4.24,0,0,0-2.5,4.17c0,9.12,1.49,6.54-6.46,11.15C66,113.71,55.24,119.72,44.5,125.82c-.85.48-1.63,1.08-2.45,1.62Z"
          className={`fill-none stroke-current`}
          stroke={strokeColor}
          strokeWidth="2"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: {
              pathLength: 1,
              opacity: 1,
              transition: { duration: 2, ease: "easeInOut" }
            },
            thinking: {
              opacity: 1,
              pathLength: [0, 1, 0],
              transition: { duration: 1.5, repeat: Infinity, ease: "linear" }
            }
          }}
        />
        <motion.path
          d="M44.35,119.84c1.25-.64,2.13-1,3-1.51,9.31-5.37,18.58-10.82,28-16.09a4.58,4.58,0,0,0,2.65-4.69q-.12-43.51,0-87V7.2c-1.28.68-2.14,1.1-3,1.58-9.32,5.37-18.58,10.82-28,16.06-2.07,1.16-2.63,2.45-2.62,4.7q.11,43.5.05,87Z"
          className={`fill-none stroke-current`}
          stroke={strokeColor}
          strokeWidth="2"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: {
              pathLength: 1,
              opacity: 1,
              transition: { duration: 2, delay: 0.5, ease: "easeInOut" }
            },
            thinking: {
              opacity: 1,
              pathLength: [0, 1, 0],
              transition: { duration: 1.5, delay: 0.2, repeat: Infinity, ease: "linear" }
            }
          }}
        />
        <motion.path
          d="M5.65,62.08c-.09.82-.19,1.28-.19,1.74,0,11.66-.06,23.33.08,35a4.41,4.41,0,0,0,2.05,3.06C17.1,107.5,26.69,113,36.27,118.5c.74.42,1.53.75,2.3,1.12.19-.38.34-.54.34-.7,0-12,.07-23.93,0-35.89a3.93,3.93,0,0,0-1.8-2.64c-4.14-2.56-8.4-5-12.62-7.4Z"
          className={`fill-none stroke-current`}
          stroke={strokeColor}
          strokeWidth="2"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: {
              pathLength: 1,
              opacity: 1,
              transition: { duration: 2, delay: 1, ease: "easeInOut" }
            },
            thinking: {
              opacity: 1,
              pathLength: [0, 1, 0],
              transition: { duration: 1.5, delay: 0.4, repeat: Infinity, ease: "linear" }
            }
          }}
        />
        <motion.path
          d="M83.25,7.08c0,12.43.06,24.18-.06,35.92a4.15,4.15,0,0,0,2.48,4.16C95,52.48,104.26,57.91,113.55,63.3c.83.48,1.69.89,2.62,1.37a5.29,5.29,0,0,0,.33-1.1c0-11.85.08-23.7,0-35.55a4,4,0,0,0-1.83-2.65c-4.93-3-10-5.84-14.94-8.73Z"
          className={`fill-none stroke-current`}
          stroke={strokeColor}
          strokeWidth="2"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: {
              pathLength: 1,
              opacity: 1,
              transition: { duration: 2, delay: 1.5, ease: "easeInOut" }
            },
            thinking: {
              opacity: 1,
              pathLength: [0, 1, 0],
              transition: { duration: 1.5, delay: 0.6, repeat: Infinity, ease: "linear" }
            }
          }}
        />
        <motion.path
          d="M38.72,75V39.73L8.28,57.3Z"
          className={`fill-none stroke-current`}
          stroke={strokeColor}
          strokeWidth="2"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: {
              pathLength: 1,
              opacity: 1,
              transition: { duration: 2, delay: 2, ease: "easeInOut" }
            },
            thinking: {
              opacity: 1,
              pathLength: [0, 1, 0],
              transition: { duration: 1.5, delay: 0.8, repeat: Infinity, ease: "linear" }
            }
          }}
        />
        <motion.path
          d="M113.72,69.83L83.41,52.23V87.34Z"
          className={`fill-none stroke-current`}
          stroke={strokeColor}
          strokeWidth="2"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: {
              pathLength: 1,
              opacity: 1,
              transition: { duration: 2, delay: 2.5, ease: "easeInOut" }
            },
            thinking: {
              opacity: 1,
              pathLength: [0, 1, 0],
              transition: { duration: 1.5, delay: 1, repeat: Infinity, ease: "linear" }
            }
          }}
        />
      </motion.svg>
    </div>
  )
}