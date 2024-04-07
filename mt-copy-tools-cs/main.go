package main

import (
	"fmt"
	"crypto/md5"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/sha512"
	"io"
	"hash"
	"errors"
	"strconv"
	"os"
	"github.com/akamensky/argparse"
)

func main(){
	parser := argparse.NewParser(os.Args[0], "Calculates check sum of a piece of a file")
	filename := parser.String("f", "file", &argparse.Options{Required:true})
	start_str := parser.String("s", "start", &argparse.Options{Help:"start position within a file",Default:"0"})
	length_str := parser.String("l", "length", &argparse.Options{Help:"length of a piece. 0 means all",Default:"0"})
	hashMethod := parser.String("m", "method", &argparse.Options{Help:"Hash method. md5,sha1,sha256,sha512",Default:"md5"})

	if err := parser.Parse(os.Args); err != nil {
		fmt.Fprintf(os.Stderr, "Argument parser error: %v\n", err)
		fmt.Fprint(os.Stderr, parser.Usage(err))
		os.Exit(1)
	}

	start, err := strconv.ParseInt(*start_str, 10, 64)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error during converting the start argument to int64: %v", err)
		os.Exit(7)
	}

	length, err := strconv.ParseInt(*length_str, 10, 64)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error during converting the length argument to int64: %v", err)
		os.Exit(8)
	}

	var hash_engine hash.Hash
	switch *hashMethod {
	case "md5":
		hash_engine = md5.New()
	case "sha1":
		hash_engine = sha1.New()
	case "sha256":
		hash_engine = sha256.New()
	case "sha512":
		hash_engine = sha512.New()
	default:
		fmt.Fprintf(os.Stderr, "Unsupported hash method %v\n", *hashMethod)
		os.Exit(5)
	}

	file, err := os.Open(*filename)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error during opening the file %s: %v\n", *filename, err)
		os.Exit(2)
	}
	defer file.Close()

	if length == 0 {
		fileinfo, err := file.Stat()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error during gathering file stats: %v", err)
			os.Exit(3)
		}

		length = fileinfo.Size() - start
	}

	written, err := io.CopyN(hash_engine, io.NewSectionReader(file, start, length), length)
	if err != nil {
		if errors.Is(err, io.EOF) {
			fmt.Fprintf(os.Stderr, "meet EOF too early, read only %v bytes of wanted %v\n", written, length)
		} else {
			fmt.Fprintf(os.Stderr, "Error during reading the file: %v\n", err)
			os.Exit(6)
		}
	}

	fmt.Printf("%x\n", hash_engine.Sum(nil))

	return
}
