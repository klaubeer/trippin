"use client";

import dynamic from "next/dynamic";

const VideoFundo = dynamic(() => import("./VideoFundo"), { ssr: false });

export default function VideoFundoDinamico() {
  return <VideoFundo />;
}
